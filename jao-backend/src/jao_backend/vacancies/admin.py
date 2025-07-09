from django.contrib import admin

from jao_backend.common.admin import ReadOnlyAdminMixin
from jao_backend.vacancies.models import Vacancy
from jao_backend.vacancies.models import VacancyGrade


class StatusFilter(admin.SimpleListFilter):
    title = "status"
    parameter_name = "status"

    def choices(self, changelist):
        # Remove default "All" choice
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
        return value if value is not None else "active"


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


@admin.register(Vacancy)
class VacancyAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "title", "min_salary", "max_salary", "last_updated")
    search_fields = ("title", "description", "summary")
    list_filter = (StatusFilter, "last_updated")
    ordering = ("-last_updated",)
    inlines = [VacancyGradeInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
