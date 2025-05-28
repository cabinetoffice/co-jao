# inline_exceptions/templatetags/inline_exceptions_tags.py
import json
import pickle
import uuid

from django import template
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe

register = template.Library()


import pickle
import uuid

from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def render_inline_exception(context, exception):
    if not settings.DEBUG:
        return ""

    request = context.get("request")
    if request is None:
        return mark_safe("<p>Error: Request context is not available.</p>")

    # Render the exception details using the template fragment
    problem_details_html = render_to_string(
        "problem_details.html",
        {
            "problem_details": (
                exception.problem_details
                if hasattr(exception, "problem_details")
                else None
            )
        },
        request=request,
    )

    return mark_safe(problem_details_html)
