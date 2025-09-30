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

# from jao_backend_schemas.maps import AreaFrequenciesResponse
# from jao_backend_schemas.plots import PlotlyFiguresResponse
from jao_backend_schemas.advice import AdviceResponse
from jao_backend_schemas.vacancies import SimilarVacanciesResponse

from jao_web.job_advert_optimiser.services.services import get_advice
from jao_web.job_advert_optimiser.services.services import get_applicant_locations
from jao_web.job_advert_optimiser.services.client import get_async_client
# from jao_web.job_advert_optimiser.services.services import get_demographics_plots
from jao_web.job_advert_optimiser.services.services import get_similar_adverts
# from jao_web.job_advert_optimiser.services.services import get_skills_plots
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
    ]:

        # Use django channels to reimplement with a websocket
        # Once websocket is open, send one thing
        #  The backend will hadle sending things back as they're ready
        session_key = self.get_or_create_session_key()
        async with get_async_client(session_key) as client:
            results = await asyncio.gather(
                get_advice(client, job_description),
                get_similar_adverts(client, job_description),
                return_exceptions=True,
            )
        return results

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
        ) = await self.get_data(job_description)

        print(f"HERE THEE HERON:__________\n{advice_response}\n_________")

        logger.info(f"\n=== ADVICE RESPONSE ===")
        logger.info(f"Type: {type(advice_response)}")
        logger.info(f"Is Exception: {isinstance(advice_response, Exception)}")
        if isinstance(advice_response, Exception):
            logger.info(f"Exception: {advice_response}")
            advice = None
        else:
            logger.info(f"Response object: {advice_response}")
            logger.info(f"Has advice attr: {
                        hasattr(advice_response, 'advice')}")
            if hasattr(advice_response, 'advice'):
                advice = advice_response.advice
                logger.info(f"Advice content: {advice}")
            else:
                logger.info(f"Available attributes: {dir(advice_response)}")
                advice = str(advice_response)

        # Debug similar vacancies
        logger.info(f"\n=== SIMILAR VACANCIES RESPONSE ===")
        logger.info(f"Type: {type(similar_vacancies_response)}")
        logger.info(f"Is Exception: {isinstance(
            similar_vacancies_response, Exception)}")
        if isinstance(similar_vacancies_response, Exception):
            logger.info(f"Exception: {similar_vacancies_response}")
            similar_vacancies = []
        else:
            logger.info(f"Response object: {similar_vacancies_response}")
            logger.info(f"Has similar_vacancies attr: {
                hasattr(similar_vacancies_response, 'similar_vacancies')}")
            if hasattr(similar_vacancies_response, 'similar_vacancies'):
                similar_vacancies = similar_vacancies_response.similar_vacancies
                logger.info(f"Vacancies count: {len(similar_vacancies)}")
                if similar_vacancies:
                    logger.info(f"First vacancy: {similar_vacancies[0]}")
                    logger.info(f"First vacancy type: {
                                type(similar_vacancies[0])}")
            else:
                logger.info(f"Available attributes: {
                    dir(similar_vacancies_response)}")
                similar_vacancies = []

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

        advice = advice_response.advice if advice_response else None
        similar_vacancies = (
            similar_vacancies_response.similar_vacancies
            if similar_vacancies_response
            else []
        )

        print(service_errors)

        context = self.get_context_data(form=form)
        context.update(
            {
                "show_extra_widgets": True,
                "job_advert_advice": advice,
                "similar_vacancies": similar_vacancies,
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
