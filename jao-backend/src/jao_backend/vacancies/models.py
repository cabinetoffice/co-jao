from django.conf import settings
from django.db import models

from jao_backend.embeddings.models import TaggedEmbedding, EmbeddingTag
from jao_backend.roles.models import Grade
from jao_backend.roles.models import RoleType
from jao_backend.vacancies.querysets import VacancyQuerySet
from jao_backend.vacancies.querysets import VacancyEmbeddingQuerySet


class Vacancy(models.Model):
    class Meta:
        verbose_name_plural = "Vacancies"
        indexes = [
            models.Index(fields=["is_deleted"]),
        ]

    id = models.IntegerField(
        primary_key=True, help_text="CS Jobs vacancy ID [5-6 characters]"
    )

    last_updated = models.DateTimeField(help_text="Last updated date and time.")

    live_date = models.DateTimeField()
    closing_date = models.DateTimeField()

    is_deleted = models.BooleanField(
        default=False, help_text="Vacancy is marked as deleted."
    )
    """
    This ID is synchronised to vacancy_id in the R2D2 database.
    """

    min_salary = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="The minimum salary.", null=True
    )
    max_salary = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="The maximum salary.", null=True
    )

    title = models.TextField(null=True, blank=True, help_text="Job title.")
    description = models.TextField(null=True, blank=True, help_text="Job description.")
    summary = models.TextField(null=True, blank=True, help_text="Blerb about teams.")
    person_spec = models.TextField(null=True, blank=True, help_text="The person specification of a vacancy")

    grades = models.ManyToManyField(
        through="VacancyGrade", to=Grade, help_text="The grades of the vacancy."
    )
    role_types = models.ManyToManyField(
        through="VacancyRoleType",
        to=RoleType,
        help_text="The role types of the vacancy.",
    )

    objects = VacancyQuerySet.as_manager()

    def get_requires_embedding(self):
        """
        For queries on whether the vacancy requires embedding use .requires_embedding()
        `VacancyQuerySet`.

        For a single Vacancy, if it's required to recalculate when embedding is required
        then this method can be used (e.g. in task, to guard against concurrency).
        """
        expected_embed_tag_uuids = list(EmbeddingTag.get_configured_tags().keys())
        expected_tags_count = len(expected_embed_tag_uuids)
        return (
            self.vacancyembedding_set.filter(
                tag__uuid__in=expected_embed_tag_uuids
            ).count()
            < expected_tags_count
        )

    def __str__(self):
        return f"{self.id, self.title}"


class VacancyGrade(models.Model):
    """
    A Vacancy can have many grades.
    """

    vacancy = models.ForeignKey(
        Vacancy, on_delete=models.CASCADE, help_text="The vacancy."
    )
    grade = models.ForeignKey(
        Grade, on_delete=models.CASCADE, help_text="The grade of the vacancy."
    )

    class Meta:
        unique_together = ("vacancy", "grade")
        verbose_name_plural = "Vacancy Grades"

    def __str__(self):
        return f"{self.vacancy.title} - {self.grade.description}"


class VacancyRoleType(models.Model):
    """
    A Vacancy can have many grades.
    """

    vacancy = models.ForeignKey(
        Vacancy, on_delete=models.CASCADE, help_text="The vacancy."
    )
    role_type = models.ForeignKey(
        RoleType, on_delete=models.CASCADE, help_text="The role type of the vacancy."
    )

    class Meta:
        unique_together = ("vacancy", "role_type")
        verbose_name_plural = "Vacancy Grades"

    def __str__(self):
        return f"{self.vacancy.title} - {self.role_type.description}"





class VacancyEmbeddingManager(models.Manager):
    def get_queryset(self):
        return VacancyEmbeddingQuerySet(self.model, using=self._db)

    def similar_vacancies(text, tag: EmbeddingTag, top_n=10):
        """
        Get vacancies similar to the provided text.

        :param text: The text to compare against vacancy responsibilities.
        :param tag: The EmbeddingTag to use for similarity comparison.
        :param top_n: The number of similar vacancies to return (default is 10).

        EmbeddingTag stores tag uuid and embedding model to use.

        >>> tag = EmbeddingTag.get_tag(settings.EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID)
        ... similar_vacancies = VacancyEmbedding.objects.similar_vacancies("Sample job description", tag)
        ... print(similar_vacancies.values_list("id", "title", flat=True))
        """
        response = tag.embed(text)
        chunks = tag.response_chunks(response)

        # If there are many chunks we sue the mean.
        if len(chunks) > 1:
            chunking_strategy = MeanStrategy()
            query_vector = chunking_strategy.chunk(chunks)
        else:
            query_vector = chunks[0]  # for now take the first chunk

        vacancy_embeddings = (
            VacancyEmbedding.objects.filter(tag=tag)
            .distance(query_vector)
            .select_related("vacancy", "embedding")
            .order_by("distance")[:top_n]
        )

        return vacancy_embeddings

class VacancyEmbedding(TaggedEmbedding):
    """
    A Vacancy can have many embeddings.
    """

    vacancy = models.ForeignKey(
        Vacancy, on_delete=models.CASCADE, help_text="The vacancy."
    )

    allowed_tags = [
        settings.EMBEDDING_TAG_JOB_TITLE_RESPONSIBILITIES_ID,
    ]

    deprecated_tags = []

    objects = VacancyEmbeddingManager.from_queryset(VacancyEmbeddingQuerySet)()


    class Meta:
        unique_together = ("vacancy", "tag", "embedding")
        verbose_name_plural = "Vacancy Embeddings"

        constraints = [
            models.UniqueConstraint(
                fields=["vacancy", "tag", "embedding", "chunk_index"],
                name="unique_vacancy_embedding_chunk",
            ),
        ]


    def __str__(self):
        return f"{self.vacancy.title} - {self.tag.name}"
