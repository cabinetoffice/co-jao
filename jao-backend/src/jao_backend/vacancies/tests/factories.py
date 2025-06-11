import factory
import random
from factory.faker import Faker
from decimal import Decimal
from django.utils import timezone

from jao_backend.vacancies.models import Vacancy


class VacancyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vacancy

    id = factory.Sequence(lambda n: 10000 + n)
    last_updated = factory.LazyFunction(timezone.now)
    title = Faker("job")
    description = Faker("paragraph", nb_sentences=8)
    summary = Faker("paragraph", nb_sentences=3)
    min_salary = Faker("random_number", digits=5, fix_len=True)

    @factory.lazy_attribute
    def max_salary(self):
        if random.random() < 0.15:
            return None

        return Decimal(self.min_salary) + Decimal(random.randint(1000, 5000))
