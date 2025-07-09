"""
Sanity checks to verify some assumptions upon which our tests rely.
"""

import pytest

from jao_backend.oleeo.models import ListAgeGroup
from jao_backend.oleeo.tests.factories import TestListAgeGroupFactory


@pytest.mark.django_db
def test_sanity_check_list_age_group_model():
    """
    TestListAgeGroup should mirror the OLEEO ListAgeGroup model, as the tests built
    on it assume the fields are the same.

    The exception is foreign keys:  we don't model them in the test model,

    Note to future devs:
    If this test fails adjust the model to match not this test.
    """
    exclude_fields = {"dandi"}

    # Use repr as it encompasses the type and name:
    expected_field_names = {
        repr(field) for field in TestListAgeGroupFactory._meta.model._meta.get_fields()
    }

    actual_field_names = {
        repr(field)
        for field in ListAgeGroup._meta.get_fields()
        if field.name not in exclude_fields
    }

    assert expected_field_names == actual_field_names
