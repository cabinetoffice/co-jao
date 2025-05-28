from django.contrib import admin
from .models import Department


@admin.register(Department)
class DepartmentsAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")
