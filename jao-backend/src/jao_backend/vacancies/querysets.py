from django.db import models


class VacancyQuerySet(models.QuerySet):

    def annotate_responsibilities(self):
        """
        Responsibilities is summary and description concatenated.

        JAO only has aggregated data unlike PEGA which
        includes length of employment as the first field.
        """
        return self.annotate(
            responsibilities=(
                models.F("summary") + models.Value("\n") + models.F("description")
            )
        )
