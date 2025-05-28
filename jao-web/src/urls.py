from django.conf import settings
from django.contrib import admin
from django.urls import include
from django.urls import path

urlpatterns = [
    path("", include("jao_web.home.urls")),
    path("job_advert_optimiser/", include("jao_web.job_advert_optimiser.urls")),
    path("django-admin/", admin.site.urls),
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

    # if "inline_exceptions" in settings.INSTALLED_APPS:
    if True:
        urlpatterns.append(
            path("inline_exceptions/", include("jao_web.inline_exceptions.urls")),
        )
        path(
            "inline_exceptions/",
            include("jao_web.inline_exceptions.urls", namespace="inline_exceptions"),
        ),
