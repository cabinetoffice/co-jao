from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Case
from django.db.models import F
from django.db.models import OuterRef
from django.db.models import Subquery
from django.db.models import When
from pgvector.django.functions import CosineDistance


class PolymorphicEmbeddingQuerySetMixin:

    def polymorphic_embedding_lookup(self, base_lookup_prefix="embedding"):
        """Internal helper to build the CASE expression."""
        # ... logic to build and return the Case object ...
        when_clauses = []
        from jao_backend.embeddings.models import Embedding

        for subclass in Embedding.__subclasses__():
            if not hasattr(subclass, "embedding") or subclass._meta.abstract:
                continue

            condition_path = f"{base_lookup_prefix}__polymorphic_ctype_id"
            field_path = f"{base_lookup_prefix}__{subclass._meta.model_name}__embedding"
            ctype_id = ContentType.objects.get_for_model(subclass).pk

            when_clauses.append(When(**{condition_path: ctype_id}, then=F(field_path)))

        return Case(*when_clauses) if when_clauses else None

    def distance(
        self,
        query_vector,
        base_lookup_prefix="embedding",
        distance_function=CosineDistance,
    ):
        """High-level method to annotate distance."""
        if not callable(distance_function):
            raise TypeError("distance_function must be a callable")

        # It calls the helper method and passes the prefix.
        embedding_case = self.polymorphic_embedding_lookup(
            base_lookup_prefix=base_lookup_prefix
        )

        if embedding_case is None:
            return self.none()

        return self.annotate(distance=distance_function(embedding_case, query_vector))


class EmbeddingTagQuerySet(models.QuerySet, PolymorphicEmbeddingQuerySetMixin):
    def configured_models(self):
        """
        Embeddings for different models can coexist in the database, this filters down
        to only return tags configured in settings
        """
        valid_tags = [
            embedding_tag.pk
            for embedding_tag in self.model.get_configured_tags().values()
        ]
        return self.filter(pk__in=valid_tags)

    def current_version(self):
        """
        Ensure that we only get the latest version of each embedding tag.
        """

        model = self.model
        latest_version_subquery = (
            model.objects.filter(uuid=OuterRef("uuid"))
            .order_by("-version")
            .values("version")[:1]
        )

        qs = self.filter(version=Subquery(latest_version_subquery))

        return qs

    def valid_tags(self):
        """
        Latest version tags, configured for this deployment.
        """
        return self.configured_models().current_version()
