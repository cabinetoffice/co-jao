# from django.test import SimpleTestCase
# import pytest
import warnings

from django.urls import reverse

from jao_web.job_advert_optimiser.forms import JobAdvertForm


def test_initial_form_appears(client):
    """
    On initial load the user should be presented with the form to enter a job description.
    """
    url = reverse("job_advert_optimiser")
    result = client.get(url)

    assert result.status_code == 200
    assert isinstance(result.context["form"], JobAdvertForm)
