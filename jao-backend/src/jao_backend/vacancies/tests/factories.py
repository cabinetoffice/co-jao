import factory

from factory.faker import Faker
from decimal import Decimal

from jao_backend.vacancies.models import Vacancy


class VacancyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vacancy

    id = factory.Sequence(lambda n: 10000 + n)
    min_salary = Faker('random_number', digits=5, fix_len=True)

    @factory.lazy_attribute
    def max_salary(self):
        # Get a new Faker instance
        fake = Faker._get_faker()
        # Return None 15% of the time or min_salary + random increment
        return None if fake.boolean(chance_of_getting_true=15) else \
            Decimal(self.min_salary) + Decimal(fake.random_int(min=5000, max=30000))

    job_title = Faker('job')
    job_description = Faker('paragraph', nb_sentences=8)
    summary = Faker('paragraph', nb_sentences=3)
    responsibilities = Faker('paragraph', nb_sentences=5)
