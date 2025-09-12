from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Submit as GovSubmit
from django import forms
from django.conf import settings


class IngestForm(forms.Form):
    batch_size = forms.IntegerField(
        required=False, initial=50000, label="Max Batch Size"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout("batch_size", GovSubmit("submit", "Start Ingest"))


class EmbedForm(forms.Form):
    batch_size = forms.IntegerField(
        required=False,
        initial=settings.JAO_BACKEND_VACANCY_EMBED_BATCH_SIZE,
        label="Vacancies to ingest",
        max_value=settings.JAO_BACKEND_VACANCY_EMBED_BATCH_SIZE,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "batch_size", "s3_url", GovSubmit("submit", "Start Embedding")
        )
