"""
Note:  It's assumed that during test the database is not pointing at the live OLEEO data !
"""

import factory
from faker import Faker

from jao_backend.oleeo.tests.models import TestListAgeGroup
from jao_backend.oleeo.tests.models import TestVacancies
from jao_backend.oleeo.tests.models import TestVacanciesTimestamps

fake = Faker()


class TestListAgeGroupFactory(factory.django.DjangoModelFactory):
    """Factory for creating TestListAgeGroup instances."""

    class Meta:
        model = TestListAgeGroup

    age_group_id = factory.Sequence(lambda n: n)
    age_group_desc = factory.Faker("word")
    row_last_updated = factory.Faker(
        "date_time_this_decade", before_now=True, after_now=False
    )


class TestVacanciesTimestampsFactory(factory.django.DjangoModelFactory):
    """Factory for creating TestVacanciesTimestamps instances.
    Typically used as a SubFactory for TestVacancies.
    """

    class Meta:
        model = TestVacanciesTimestamps

    vacancy = factory.SubFactory(
        "jao_backend.oleeo.tests.factories.TestVacanciesFactory"
    )
    live_date = factory.Faker("date_time_between", start_date="-30d", end_date="now")
    closing_date = factory.Faker("date_time_between", start_date="now", end_date="+90d")


class TestVacanciesFactory(factory.django.DjangoModelFactory):
    """Factory for creating valid TestVacancies instances."""

    class Meta:
        model = TestVacancies
        skip_postgeneration_save = True

    vacancy_id = factory.Sequence(lambda n: n)
    vacancy_title = factory.Faker("job")
    salary_minimum = factory.Faker("random_int", min=30000, max=80000)
    salary_maximum_optional = factory.Faker("random_int", min=50000, max=120000)

    @factory.post_generation
    def convert_salaries_to_string_and_save(obj, create, extracted, **kwargs):
        """
        Convert salary fields to strings and save the object.
        Required because skip_postgeneration_save is True.
        """
        if create:
            if obj.salary_minimum is not None:
                obj.salary_minimum = str(obj.salary_minimum)
            if obj.salary_maximum_optional is not None:
                obj.salary_maximum_optional = str(obj.salary_maximum_optional)
            obj.save()

    @factory.post_generation
    def create_timestamp(obj, create, extracted, **kwargs):
        """Create associated TestVacanciesTimestamps for each vacancy."""
        if create:
            TestVacanciesTimestamps.objects.get_or_create(
                vacancy=obj,
                defaults={
                    "live_date": fake.date_time_between(
                        start_date="-30d", end_date="now"
                    ),
                    "closing_date": fake.date_time_between(
                        start_date="now", end_date="+90d"
                    ),
                },
            )


class InvalidTestVacanciesFactory(TestVacanciesFactory):
    """Factory for creating invalid vacancy test data with various bad salary formats."""

    class Params:
        invalid_type = factory.Trait(salary_minimum=None)
        comma_in_salary = factory.Trait(
            salary_minimum="50,000", salary_maximum_optional="60,000"
        )
        text_salary = factory.Trait(
            salary_minimum="fifty thousand", salary_maximum_optional="sixty thousand"
        )
        very_large_number = factory.Trait(salary_minimum="999999999999999999999")

    @factory.post_generation
    def convert_salaries_to_string_and_save(obj, create, extracted, **kwargs):
        """
        Overrides parent to save invalid salary formats directly without conversion.
        Required because skip_postgeneration_save is True.
        """
        if create:
            obj.save()
