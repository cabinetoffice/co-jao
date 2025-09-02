from django.contrib import admin, messages
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import path
from django.conf import settings
from django import forms

from jao_backend.common.admin import ReadOnlyAdminMixin
from jao_backend.common.celery.monitoring import is_task_running
from jao_backend.embeddings.models import EmbeddingTag
from jao_backend.vacancies.models import Vacancy, VacancyGrade, VacancyRoleType
from jao_backend.vacancies.tasks import embed_vacancies


class StartEmbeddingsTaskForm(forms.Form):
    pass


class StatusFilter(admin.SimpleListFilter):
    title = "status"
    parameter_name = "status"

    def choices(self, changelist):
        for lookup, title in self.lookup_choices:
            yield {
                "selected": self.value() == lookup,
                "query_string": changelist.get_query_string(
                    {self.parameter_name: lookup}
                ),
                "display": title,
            }

    def lookups(self, request, model_admin):
        return (
            ("active", "Active only"),
            ("deleted", "Deleted only"),
            ("all", "Active and deleted"),
        )

    def queryset(self, request, queryset):
        if self.value() == "deleted":
            return queryset.filter(is_deleted=True)
        elif self.value() == "all":
            return queryset
        return queryset.filter(is_deleted=False)

    def value(self):
        value = super().value()
        return "active" if value is None else value


class VacancyGradeInline(admin.TabularInline):
    model = VacancyGrade
    verbose_name = "Grade"
    verbose_name_plural = "Grades"
    extra = 0
    fields = ("grade",)
    readonly_fields = ("grade",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class VacancyRoleTypeInline(admin.TabularInline):
    model = VacancyRoleType
    verbose_name = "Role Type"
    verbose_name_plural = "Role Types"
    extra = 0
    fields = ("role_type",)
    readonly_fields = ("role_type",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Vacancy)
class VacancyAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "title", "min_salary", "max_salary", "last_updated")
    search_fields = ("title", "description", "summary")
    list_filter = (StatusFilter, "last_updated")
    ordering = ("-last_updated",)
    inlines = [VacancyGradeInline, VacancyRoleTypeInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "embeddings/",
                self.admin_site.admin_view(self.embeddings_view),
                name="vacancies_vacancy_embeddings",
            )
        ]
        return custom_urls + urls

    def embeddings_view(self, request):
        task_name = "jao_backend.vacancies.tasks.embed_vacancies"

        if request.method == "POST":
            form = StartEmbeddingsTaskForm(request.POST)
            if form.is_valid():
                if is_task_running(task_name):
                    messages.warning(request, "An embedding task is already running.")
                else:
                    embed_vacancies.delay()
                    messages.success(request, "Embedding task has been started.")
            return redirect(request.path_info)

        task_is_running = is_task_running(task_name)
        embed_limit = getattr(settings, 'JAO_BACKEND_VACANCY_EMBED_LIMIT', None)

        total_vacancies = Vacancy.objects.filter(is_deleted=False).count()

        configured_vacancies_qs = Vacancy.objects.configured_for_embed(limit=embed_limit)
        progress_max = configured_vacancies_qs.count()

        vacancies_needing_embedding = Vacancy.objects.requires_embedding(limit=embed_limit)
        remaining_work_count = vacancies_needing_embedding.count()

        embedding_stats = self._get_embedding_statistics(configured_vacancies_qs, progress_max)

        context = {
            **self.admin_site.each_context(request),
            "title": "Vacancy Embeddings",
            "litellm_custom_provider": settings.LITELLM_CUSTOM_PROVIDER,
            "total_vacancies": total_vacancies,
            "progress_max": progress_max,
            "remaining_work_count": remaining_work_count,
            "embedding_stats": embedding_stats,
            "embed_limit": embed_limit,
            "task_is_running": task_is_running,
            "form": StartEmbeddingsTaskForm(),
        }
        return render(request, "admin/vacancies/embedding_status.html", context)

    def _get_embedding_statistics(self, configured_vacancies_qs, progress_max):
        """
        Helper method to calculate embedding statistics for each valid tag.
        Uses the existing valid_tags() queryset method.
        """
        if progress_max == 0:
            return []

        # Use the existing valid_tags queryset method
        valid_tags = (
            EmbeddingTag.objects.valid_tags()
            .annotate(
                embedded_count=Count(
                    "vacancyembedding__vacancy",
                    filter=Q(vacancyembedding__vacancy__in=configured_vacancies_qs),
                    distinct=True,
                )
            )
            .select_related("model")
            .order_by("name")
        )

        embedding_stats = []
        for tag in valid_tags:
            percentage = (tag.embedded_count / progress_max * 100) if progress_max > 0 else 0

            embedding_stats.append({
                "tag": tag,
                "embedded_count": tag.embedded_count,  # Keep original template variable name
                "percentage": f"{percentage:.1f}",
            })

        return embedding_stats