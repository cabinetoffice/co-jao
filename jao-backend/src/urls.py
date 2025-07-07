from django.conf import settings
from django.contrib import admin
from django.urls import include
from django.urls import path
from django.http import HttpResponse, HttpResponseForbidden
from django.core.management import call_command
from django.contrib.auth import get_user_model
import sys
import io
import os
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    return HttpResponse("OK", content_type="text/plain")

def run_migrations(request):
    """Run Django migrations via web endpoint - secured"""
    if not settings.DEBUG:
        return HttpResponseForbidden("Migrations endpoint disabled in production")

    try:
        from django.db import connection

        # Test database connection first
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                db_status = "Database connection: OK"
        except Exception as db_e:
            return HttpResponse(f"Database connection failed: {str(db_e)}", status=500, content_type="text/plain")

        # Capture output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        sys.stdout = stdout_buffer
        sys.stderr = stderr_buffer

        # Run migrations
        try:
            call_command('migrate', verbosity=2)
            migration_status = "SUCCESS"
        except Exception as migrate_e:
            migration_status = f"FAILED: {str(migrate_e)}"

        # Restore stdout/stderr and get output
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        stdout_output = stdout_buffer.getvalue()
        stderr_output = stderr_buffer.getvalue()

        response_text = f"""Migration Status: {migration_status}

{db_status}

=== STDOUT ===
{stdout_output}

=== STDERR ===
{stderr_output}
"""

        return HttpResponse(response_text, content_type="text/plain")

    except Exception as e:
        # Restore stdout/stderr if they were changed
        sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout
        sys.stderr = old_stderr if 'old_stderr' in locals() else sys.stderr

        import traceback
        error_details = traceback.format_exc()
        return HttpResponse(f"Migration endpoint error:\n{str(e)}\n\nFull traceback:\n{error_details}", status=500, content_type="text/plain")

def create_superuser(request):
    """Create Django superuser via web endpoint - secured"""
    if not settings.DEBUG:
        return HttpResponseForbidden("Superuser creation endpoint disabled in production")

    User = get_user_model()

    # Use credentials from environment or defaults
    username = request.GET.get('username', 'admin')
    email = request.GET.get('email', 'admin@example.com')
    password = request.GET.get('password', 'admin123')

    try:
        if User.objects.filter(username=username).exists():
            return HttpResponse(f"User '{username}' already exists", content_type="text/plain")

        user = User.objects.create_superuser(username=username, email=email, password=password)
        return HttpResponse(f"Superuser '{username}' created successfully", content_type="text/plain")

    except Exception as e:
        return HttpResponse(f"Failed to create superuser: {str(e)}", status=500, content_type="text/plain")

# Get secure admin URL from environment or use default
SECURE_ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'secure-admin-jao-2024/')

urlpatterns = [
    path("", include("jao_backend.home.urls")),
    path("api/v1/", include("jao_backend.api.urls")),
    path("ingest/", include("jao_backend.ingest.urls")),
    # Secure admin URL (configurable via environment)
    path(SECURE_ADMIN_URL, admin.site.urls),
    # Old admin URL - redirect to secure location
    path("django-admin/", lambda r: HttpResponseForbidden("Admin access restricted. Contact administrator.")),
    path("health", health_check, name="health_check"),
    path("migrate", run_migrations, name="run_migrations"),
    path("create-superuser", create_superuser, name="create_superuser"),
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
