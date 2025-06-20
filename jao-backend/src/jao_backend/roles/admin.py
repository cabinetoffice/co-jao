from django.contrib import admin
from .models import RoleType, Grade


@admin.register(RoleType)
class RoleTypeAdmin(admin.ModelAdmin):
    list_display = ('description',)
    search_fields = ('description',)
    ordering = ('description',)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('description',)
    search_fields = ('description',)
    ordering = ('description',)
