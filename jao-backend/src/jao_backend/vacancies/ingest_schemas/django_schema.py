from djantic import ModelSchema
from pydantic import ConfigDict

from jao_backend.application_statistics.models import AggregatedApplicationStatistic
from jao_backend.vacancies.models import Vacancy


class VacancySchema(ModelSchema):
    model_config = ConfigDict(
        model=Vacancy,  # type: ignore
        include=[  # type: ignore
            "id",
            "last_updated",
            "live_date",
            "closing_date",
            "min_salary",
            "max_salary",
            "title",
            "description",
            "summary",
            "person_spec"
        ],
    )


class AggregatedStatisticSchema(ModelSchema):
    model_config = ConfigDict(
        model=AggregatedApplicationStatistic,  # type: ignore
        include=[  # type: ignore
            "vacancy_id",
            "total_applications",
            "updated_at",
            "content_type",
            "object_id",
            "ratio",
        ],
    )
