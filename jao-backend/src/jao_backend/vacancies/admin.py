from django.contrib import admin
from django.db.models import Case, When, IntegerField, Value
from .models import Vacancy
# from jao_backend.roles.models import RoleType, Grade
#
#
# @admin.register(Vacancy)
# class VacancyAdmin(admin.ModelAdmin):
#     list_display = ("id", "job_title", "min_salary", "max_salary")
#     search_fields = ("id", "job_title", "job_description", "summary", "responsibilities")
#     fieldsets = (
#         (None, {"fields": ("id", "job_title")}),
#         ("Salary Information", {"fields": ("min_salary", "max_salary")}),
#         ("Job Details", {"fields": ("job_description", "summary", "responsibilities")}),
#     )
