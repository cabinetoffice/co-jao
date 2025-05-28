# from django.contrib import admin
# from .models import ApplicationStatistic
#
#
# @admin.register(ApplicationStatistic)
# class ApplicationStatisticAdmin(admin.ModelAdmin):
#     list_display = (
#         "id",
#         "vacancy",
#         "total_applications",
#         "passed_sift",
#         "offer",
#         "created_at",
#     )
#     list_filter = ("vacancy", "created_at")
#     search_fields = ("vacancy__id", "vacancy__job_title")
#     raw_id_fields = ("vacancy",)
#
#     fieldsets = (
#         (None, {"fields": ("vacancy",)}),
#         (
#             "Application Status",
#             {
#                 "fields": (
#                     "total_applications",
#                     "average_applicant_score",
#                     "failed_sift_1",
#                     "failed_sift_2",
#                     "passed_sift",
#                     "failed_interview",
#                     "offer",
#                     "reserve",
#                 )
#             },
#         ),
#         (
#             "Age Group",
#             {
#                 "fields": (
#                     "age_group_16_24",
#                     "age_group_25_29",
#                     "age_group_30_34",
#                     "age_group_35_39",
#                     "age_group_40_44",
#                     "age_group_45_49",
#                     "age_group_50_54",
#                     "age_group_55_59",
#                     "age_group_60_64",
#                     "age_group_65_plus",
#                     "age_group_prefer_not_to_disclose",
#                     "age_group_restricted_data",
#                 ),
#                 "classes": ("collapse",),
#             },
#         ),
#         (
#             "Disability",
#             {
#                 "fields": (
#                     "disability_disabled",
#                     "disability_non_disabled",
#                     "disability_prefer_not_to_say",
#                     "disability_restricted_data",
#                 ),
#                 "classes": ("collapse",),
#             },
#         ),
#         (
#             "Gender",
#             {
#                 "fields": (
#                     "gender_female",
#                     "gender_male",
#                     "gender_other",
#                     "gender_prefer_not_to_say",
#                     "gender_restricted_data",
#                 ),
#                 "classes": ("collapse",),
#             },
#         ),
#         (
#             "Ethnic Group",
#             {
#                 "fields": (
#                     "ethnic_group_asian_asian_british",
#                     "ethnic_group_black_african_caribbean_black_british",
#                     "ethnic_group_mixed_multiple_ethnic_groups",
#                     "ethnic_group_other",
#                     "ethnic_group_prefer_not_to_disclose",
#                     "ethnic_group_restricted_data",
#                     "ethnic_group_white",
#                 ),
#                 "classes": ("collapse",),
#             },
#         ),
#         (
#             "Socio-Economic Background",
#             {
#                 "fields": (
#                     "seb_intermediate",
#                     "seb_lower",
#                     "seb_professional",
#                     "seb_unknown",
#                 ),
#                 "classes": ("collapse",),
#             },
#         ),
#         (
#             "Approach Name",
#             {
#                 "fields": (
#                     "approach_name_50",
#                     "approach_name_across_government",
#                     "approach_name_external",
#                     "approach_name_internal",
#                     "approach_name_pre_release",
#                 ),
#                 "classes": ("collapse",),
#             },
#         ),
#     )
#
#     readonly_fields = ("created_at", "updated_at")
#
#     def get_readonly_fields(self, request, obj=None):
#         """Include created_at and updated_at in readonly fields if they exist in the model"""
#         readonly_fields = list(super().get_readonly_fields(request, obj))
#         if hasattr(obj, "created_at"):
#             readonly_fields.append("created_at")
#         if hasattr(obj, "updated_at"):
#             readonly_fields.append("updated_at")
#         return readonly_fields
