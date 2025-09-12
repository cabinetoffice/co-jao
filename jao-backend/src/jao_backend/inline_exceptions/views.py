import pickle
import sys

from django.conf import settings
from django.http import HttpResponse
from django.views.debug import ExceptionReporter
from django.views.decorators.clickjacking import xframe_options_exempt


def require_debug_mode(view):
    def wrapped(request, *args, **kwargs):
        if not settings.DEBUG:
            return HttpResponse("Debug mode is off.", status=403)
        return view(request, *args, **kwargs)

    return wrapped


@xframe_options_exempt
@require_debug_mode
def exception_view(request, exc_id):
    serialized_exception = request.session.get(f"exception_{exc_id}")
    if not serialized_exception:
        return HttpResponse("Exception not found.", status=404)

    exception = pickle.loads(serialized_exception)

    exc_type, exc_value, tb = sys.exc_info()
    if exc_value is not exception:
        exc_type, exc_value, tb = type(exception), exception, exception.__traceback__

    reporter = ExceptionReporter(request, exc_type, exc_value, tb)
    html = reporter.get_traceback_html()

    response = HttpResponse(html)
    response["Content-Security-Policy"] = "frame-ancestors 'self'"

    return response
