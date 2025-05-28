from django.db.models.signals import post_save
from django.dispatch import receiver

from jao_backend.embeddings.tasks import generate_embeddings_task
from jao_backend.vacancies.models import Vacancy


@receiver(post_save, sender=Vacancy)
def handle_vacancy_update(sender, instance, created, **kwargs):
    """
    Signal handler for vacancy changes. Triggered on Vacancy save:
    - New vacancies: Generate embeddings immediately
    - Updates: Queue for re-embedding if text changed

    Args:
    - sender: Vacancy model class
    - instance: Actual Vacancy instance
    - created: Boolean indicating new record
    """
    if created or instance.tracker.has_changed(("summary", "responsibilities")):
        generate_embeddings_task.delay(instance.id)
