import os

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

ADMIN_URL = os.environ.get("DJANGO_ADMIN_URL", "django-admin/")

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path("health", include("jao_backend.healthcheck.urls")),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()

    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
