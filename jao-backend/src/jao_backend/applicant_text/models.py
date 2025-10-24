from django.db import models

class ApplicationText(models.Model):
    """
    Stores the raw, free-form text for a SINGLE application.
    This is our "landing zone" for Oleeo data.
    """
    vacancy = models.ForeignKey(
        "vacancies.Vacancy",
        on_delete=models.CASCADE,
        related_name="application_texts" 
    )

    application_id = models.IntegerField(unique=True)

    personal_statement = models.TextField(blank=True, null=True)
    employment_history = models.TextField(blank=True, null=True)
    previous_skill_experience = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Application text for {self.application_id}"


class VacancyTextAggregate(models.Model):
    """
    Stores all application text AGGREGATED up to a single vacancy.
    This is our "reporting" model.
    """
    vacancy = models.OneToOneField(
        "vacancies.Vacancy",
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="aggregated_text"
    )

    all_personal_statements = models.TextField(blank=True)
    all_employment_history = models.TextField(blank=True)
    all_previous_skills = models.TextField(blank=True)

    def __str__(self):
        return f"Aggregated text for {self.vacancy.pk}"