import random
from decimal import Decimal

import factory
from django.utils import timezone
from factory.faker import Faker

from jao_backend.vacancies.models import Vacancy


class VacancyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vacancy

    id = factory.Sequence(lambda n: 10000 + n)
    last_updated = factory.LazyFunction(timezone.now)
    live_date = Faker("date_time_between", start_date="-30d", end_date="now")
    closing_date = Faker("date_time_between", start_date="now", end_date="+90d")
    title = Faker("job")
    description = Faker("paragraph", nb_sentences=8)
    summary = Faker("paragraph", nb_sentences=3)
    min_salary = Faker("random_number", digits=5, fix_len=True)

    @factory.lazy_attribute
    def max_salary(self):
        if random.random() < 0.15:
            return None

        return Decimal(self.min_salary) + Decimal(random.randint(1000, 5000))
