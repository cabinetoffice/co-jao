from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Submit as GovSubmit
from django import forms
from django.conf import settings

from .fields import S3URLField


class IngestForm(forms.Form):
    max_batch_size = forms.IntegerField(required=False, initial=50000, label="Max Batch Size")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate the endpoint choices dynamically from settings

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "max_batch_size", GovSubmit("submit", "Start Ingest")
        )
