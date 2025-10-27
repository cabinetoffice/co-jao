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
    )

    def get_or_create_session_key(self):
        session = self.request.session
        session_key = session.session_key
        if not session_key:
            session.save()
            session_key = session.session_key
        return session_key

    async def get_data(self, job_description) -> SimilarVacanciesResponse:
        session_key = self.get_or_create_session_key()
        async with get_async_client(session_key) as client:
            results = await get_similar_adverts(client, job_description)
            print("RESULTS -------", results)
        return results

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "session_key": self.get_or_create_session_key(),
                'websocket_endpoint': settings.WEBSOCKET_ENDPOINT,

            }
        )
        return context

    @async_to_sync
    async def form_valid(self, form):
        context = self.get_context_data(form=form)
        context['show_extra_widgets'] = True
        return self.render_to_response(context)

    # @async_to_sync
    # async def form_valid(self, form):
    #     job_description = form.cleaned_data["job_description"]
    #     similar_vacancies_response = await self.get_data(job_description)
    #
    #     service_errors = []
    #
    #     if isinstance(similar_vacancies_response, Exception):
    #         service_errors.append(similar_vacancies_response)
    #         logger.error("Error fetching similar vacancies: %s",
    #                      format_error(similar_vacancies_response))
    #         similar_vacancies_response = None
    #
    #     similar_vacancies = (
    #         similar_vacancies_response
    #         if similar_vacancies_response
    #         else []
    #     )
    #
    #     print(service_errors)
    #
    #     context = self.get_context_data(form=form)
    #     context.update(
    #         {
    #             "show_extra_widgets": True,
    #             "similar_vacancies": similar_vacancies,
    #             "service_errors": service_errors,
    #         }
    #     )
    #     return self.render_to_response(context)

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
