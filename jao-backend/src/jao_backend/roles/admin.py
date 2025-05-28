from django.contrib import admin
from .models import Grade


class GradeAdmin(admin.ModelAdmin):
    list_display = ("description", "get_long_name", "get_numeric_value")
    search_fields = ("description",)
    list_filter = ("description",)
    ordering = ("description",)

    def get_long_name(self, obj):
        return obj.grade_long_name

    get_long_name.short_description = "Long Name"
    get_long_name.admin_order_field = "grade_long_name"

    def get_numeric_value(self, obj):
        return obj.grade_numeric

    get_numeric_value.short_description = "Level"
    get_numeric_value.admin_order_field = "grade_numeric"

    def get_queryset(self, request):
        """Override to use the custom queryset methods"""
        return Grade.objects.annotate_grade_data()

    def get_ordering(self, request):
        """Override to order by grade numeric value by default"""
        return ("grade_numeric",)


admin.site.register(Grade, GradeAdmin)
