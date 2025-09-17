from django.http import HttpResponse
import asyncio
import logging
from typing import Tuple

from asgiref.sync import async_to_sync
from django.conf import settings
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.decorators import sync_and_async_middleware
from django.views.generic.edit import FormView

from jao_backend_schemas.maps import AreaFrequenciesResponse
from jao_backend_schemas.plots import PlotlyFiguresResponse
from jao_backend_schemas.advice import AdviceResponse
from jao_backend_schemas.vacancies import SimilarVacanciesResponse

from jao_web.job_advert_optimiser.services.services import get_advice
from jao_web.job_advert_optimiser.services.services import get_applicant_locations
from jao_web.job_advert_optimiser.services.client import get_async_client
from jao_web.job_advert_optimiser.services.services import get_demographics_plots
from jao_web.job_advert_optimiser.services.services import get_similar_adverts
from jao_web.job_advert_optimiser.services.services import get_skills_plots
from jao_web.job_advert_optimiser.forms import JobAdvertForm

logger = logging.getLogger(__name__)

APPLICANT_MAP_CSS_PREFIX = "applicant-"
UK_GEOJSON_URL = settings.STATIC_URL + \
    "job_advert_optimiser/geojson/rgn2023.geojson"


def format_error(error: Exception):
    if settings.DEBUG:
        # Output the full traceback in debug mode
        # get traceback
        import traceback

        return f"{error}\n{traceback.format_exc()}"

    if len(error.args) == 1:
        return f"{error.args[0]}"

    return f"{error}"


@method_decorator(sync_and_async_middleware, name="dispatch")
class JobAdvertOptimiserView(FormView):

    template_name = "job_advert_optimiser/job_advert_optimiser.html"
    form_class = JobAdvertForm
    success_url = reverse_lazy(
        "job_advert_optimiser"
    )  # This can be any URL you want to redirect to on success

    def get_or_create_session_key(self):
        session = self.request.session
        session_key = session.session_key
        if not session_key:
            session.save()
            session_key = session.session_key
        return session_key

    async def get_data(self, job_description) -> Tuple[
        AdviceResponse,
        SimilarVacanciesResponse,
        PlotlyFiguresResponse,
        PlotlyFiguresResponse,
        AreaFrequenciesResponse,
    ]:

        # Use django channels to reimplement with a websocket
        # Once websocket is open, send one thing
        #  The backend will hadle sending things back as they're ready
        session_key = self.get_or_create_session_key()
        async with get_async_client(session_key) as client:
            results = await asyncio.gather(
                get_advice(client, job_description),
                get_similar_adverts(client, job_description),
                get_demographics_plots(client, job_description),
                get_skills_plots(client, job_description),
                get_applicant_locations(client, job_description),
                return_exceptions=True,
            )
        return results

    def get_base_map_data(self):
        """
        Map data before application data is added.
        """
        map_data = {
            "geojson_url": UK_GEOJSON_URL,
            "geojson_data": None,  # Placeholder populated by the frontend.
            "map_options": {"center": [54, -3], "zoom": 5.2},
            "layers": [
                {
                    "layer_type": "choropleth",
                    "options": {
                        "className": f"{APPLICANT_MAP_CSS_PREFIX}map-choropleth-layer"
                    },
                },
                {
                    "layer_type": "geojson",
                    "options": {
                        "className": f"{APPLICANT_MAP_CSS_PREFIX}map-no-data-layer"
                    },
                },
            ],
            "tooltip_options": {
                "fields": ["areanm", "frequency"],
                "aliases": ["Region", "Percentage of applications"],
                "className": f"{APPLICANT_MAP_CSS_PREFIX}map-tooltip-layer",
            },
        }
        return map_data

    def get_applicant_map_data(self, applicant_locations: AreaFrequenciesResponse):
        """
        Data for the applicant map.

        Note:  The geojson data is served as static data, the frontend actually requests this and
        combines it with this data.

        applicant_locations is a GeoJSON object, where each feature contains an area_name and frequency.

        :param applicant_locations: FeatureCollection
        :return:
        """
        area_frequencies = applicant_locations.model_dump()["area_frequencies"]
        map_data = {
            "area_frequencies": area_frequencies,
            **self.get_base_map_data()
        }
        return map_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "session_key": self.get_or_create_session_key(),
            }
        )
        return context

    @async_to_sync
    async def form_valid(self, form):
        job_description = form.cleaned_data["job_description"]

        (
            advice_response,
            similar_vacancies_response,
            demographics_plots,
            skills_plots,
            applicant_locations,
        ) = await self.get_data(job_description)

        # Handle possible exceptions from asyncio.gather
        service_errors = []
        if isinstance(advice_response, Exception):
            logger.error("Error fetching advice: %s",
                         format_error(advice_response))
            service_errors.append(advice_response)
            advice_response = None

        if isinstance(similar_vacancies_response, Exception):
            service_errors.append(similar_vacancies_response)
            logger.error("Error fetching similar vacancies: %s",
                         format_error(similar_vacancies_response))
            similar_vacancies_response = None

        if isinstance(demographics_plots, Exception):
            service_errors.append(demographics_plots)
            logger.error("Error fetching demographics plots: %s",
                         format_error(demographics_plots))
            demographic_figures = None
        else:
            demographic_figures = demographics_plots.get_figures()

        if isinstance(skills_plots, Exception):
            service_errors.append(skills_plots)
            logger.error("Error fetching skills plots: %s",
                         format_error(skills_plots))
            skills_figures = None
        else:
            skills_figures = skills_plots.get_figures()

        if isinstance(applicant_locations, Exception):
            logger.error("Error fetching applicant locations: %s",
                         format_error(applicant_locations))
            service_errors.append(applicant_locations)
            applicant_map_data = None
        else:
            applicant_map_data = self.get_applicant_map_data(
                applicant_locations)

        advice = advice_response.advice if advice_response else None
        similar_vacancies = (
            similar_vacancies_response.similar_vacancies
            if similar_vacancies_response
            else []
        )

        context = self.get_context_data(form=form)
        context.update(
            {
                "show_extra_widgets": True,
                "job_advert_advice": advice,
                "similar_vacancies": similar_vacancies,
                "similar_vacancies_figures": demographic_figures,
                "skills_figures": skills_figures,
                "applicant_map_data": applicant_map_data,
                "service_errors": service_errors,
            }
        )
        return self.render_to_response(context)

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        base_map_data = self.get_base_map_data()
        context.update(
            {
                "show_extra_widgets": False,
                "job_advert_advice": None,
                "similar_vacancies": [],
                "service_errors": [],
                "enable_inline_tracebacks": settings.DEBUG,
                "applicant_map_data": base_map_data,
            }
        )
        return self.render_to_response(context)


def show_client_ip(request):
    return HttpResponse(f"Your IP: {request.META.get('REMOTE_ADDR')}")
