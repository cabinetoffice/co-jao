from django.contrib import admin

from jao_backend.common.admin import ReadOnlyAdminMixin
from jao_backend.roles.models import Grade
from jao_backend.roles.models import RoleType


@admin.register(RoleType)
class RoleTypeAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "description", "last_updated", "is_deleted")
    search_fields = ("description",)
    list_filter = ("is_deleted", "last_updated")
    ordering = ("description",)


@admin.register(Grade)
class GradeAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "description", "last_updated", "is_deleted")
    search_fields = ("description",)
    list_filter = ("is_deleted", "last_updated")
    ordering = ("description",)
