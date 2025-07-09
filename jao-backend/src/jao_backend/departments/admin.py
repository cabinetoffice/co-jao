from django.contrib import admin

from jao_backend.common.admin import ReadOnlyAdminMixin
from jao_backend.departments.models import Department


@admin.register(Department)
class DepartmentsAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")
