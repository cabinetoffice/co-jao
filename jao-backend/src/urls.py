import os
import logging

from django.conf import settings
from django.contrib import admin
from django.urls import include
from django.urls import path

logger = logging.getLogger(__name__)


ADMIN_URL = os.environ.get("DJANGO_ADMIN_URL", "django-admin/")

urlpatterns = [
    path("", include("jao_backend.home.urls")),
    path("api/v0/", include("jao_backend.api.v0.urls")),
    path("api/v1/", include("jao_backend.api.urls")),
    path("ingest/", include("jao_backend.ingest.urls")),
    path(ADMIN_URL, admin.site.urls),
    path("health", include("jao_backend.healthcheck.urls")),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

    if "jao_backend.inline_exceptions" in settings.INSTALLED_APPS:
        urlpatterns.append(
            path("inline_exceptions/", include("jao_backend.inline_exceptions.urls")),
        )
        path(
            "inline_exceptions/",
            include(
                "jao_backend.inline_exceptions.urls",
                namespace="jao_backend.inline_exceptions",
            ),
        ),
