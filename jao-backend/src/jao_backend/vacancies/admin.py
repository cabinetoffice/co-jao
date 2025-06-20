from django.contrib import admin
from .models import Vacancy, VacancyGrade, VacancyEmbedding


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'min_salary', 'max_salary', 'last_updated', 'is_deleted')
    list_filter = ('is_deleted', 'last_updated')
    search_fields = ('title', 'description', 'summary')
    readonly_fields = ('last_updated',)
    ordering = ('-last_updated',)
    list_per_page = 50

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'last_updated', 'is_deleted')
        }),
        ('Salary Information', {
            'fields': ('min_salary', 'max_salary'),
            'classes': ('collapse',)
        }),
        ('Job Details', {
            'fields': ('description', 'summary'),
            'classes': ('collapse',)
        }),
    )


@admin.register(VacancyGrade)
class VacancyGradeAdmin(admin.ModelAdmin):
    list_display = ('vacancy', 'grade')
    list_filter = ('grade',)
    search_fields = ('vacancy__title', 'grade__description')
    autocomplete_fields = ('vacancy',)


@admin.register(VacancyEmbedding)
class VacancyEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('vacancy', 'tag', 'chunk_index')
    list_filter = ('tag',)
    search_fields = ('vacancy__title',)
    autocomplete_fields = ('vacancy',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('vacancy', 'tag', 'chunk_index')
        }),
        ('Embedding Data', {
            'fields': ('embedding',),
            'classes': ('collapse',)
        }),
    )
