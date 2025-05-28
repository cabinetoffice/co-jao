from django.db import models
from django.db.models import Subquery, OuterRef

from jao_backend.embeddings.models import EmbeddingTag


class EmbeddingTagQuerySet(models.QuerySet):
    def current_version(self):
        """
        Ensure that we only get the latest version of each embedding tag.
        """

        latest_version_subquery = EmbeddingTag.objects.filter(
            uuid=OuterRef('uuid')
        ).order_by('-version').values('version')[:1]

        qs = EmbeddingTag.objects.filter(
            version=Subquery(latest_version_subquery)
        )

        return qs