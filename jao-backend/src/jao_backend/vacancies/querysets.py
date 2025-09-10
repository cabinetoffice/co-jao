from django.db import models
from django.conf import settings
from django.db.models import Q
from django.db.models import Count
from django.db.models import TextField
from django.db.models import Value
from django.db.models.functions import Concat

from jao_backend.embeddings.models import EmbeddingTag
from jao_backend.embeddings.querysets import PolymorphicEmbeddingQuerySetMixin


class VacancyQuerySet(PolymorphicEmbeddingQuerySetMixin, models.QuerySet):

    def annotate_responsibilities(self):
        """
        Responsibilities is summary and description concatenated.

        JAO only has aggregated data unlike PEGA which
        includes length of employment as the first field.
        """
        return self.annotate(
            responsibilities=Concat(
                "summary", Value("\n"), "description", output_field=TextField()
            )
        )

    def configured_for_embed(self, limit=None):
        """
        Filter vacancies that are configured for embedding.

        :param limit: Optional limit on the number of vacancies to return.

        If None, it defaults to the setting `JAO_BACKEND_VACANCY_EMBED_LIMIT`, this
        may also be None, in which case all vacancies are returned.
        """
        if limit is None:
            limit = settings.JAO_BACKEND_VACANCY_EMBED_LIMIT
            # limit can still be None at this point.
        else:
            limit = min(limit, settings.JAO_BACKEND_VACANCY_EMBED_LIMIT)

        qs = self.order_by("live_date")
        if limit is None:
            return qs

        count = qs.count()
        pk = qs[max(count - limit, 0)].pk

        return qs.filter(pk__gt=pk)

    def requires_embedding(self, limit=None):
        """
        Filter vacancies that require embedding.

        This is used to filter vacancies that have not been embedded yet.
        """
        expected_embed_tag_uuids = list(EmbeddingTag.get_configured_tags().keys())
        expected_tags_count = len(expected_embed_tag_uuids)

        result = (
            self.configured_for_embed(limit=limit)
            .annotate(
                existing_tags_count=Count(
                    "vacancyembedding__tag",
                    filter=Q(vacancyembedding__tag__uuid__in=expected_embed_tag_uuids),
                    distinct=True,
                )
            )
            .filter(existing_tags_count__lt=expected_tags_count)
            .annotate_responsibilities()
        )
        return result


class VacancyEmbeddingQuerySet(PolymorphicEmbeddingQuerySetMixin, models.QuerySet):
    """
    QuerySet for VacancyEmbedding model.
    """
