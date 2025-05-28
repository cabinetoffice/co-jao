from django import forms
from django.conf import settings

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Submit as GovSubmit

from .fields import S3URLField


class S3IngestForm(forms.Form):
    s3_endpoint = forms.ChoiceField(
        label="S3 Endpoint",
        help_text="Select which S3 endpoint to use",
        choices=[],
        widget=forms.Select(attrs={"class": "govuk-select"}),
    )

    s3_url = S3URLField(
        label="S3 URL",
        help_text="Enter the S3 URL to ingest (format: s3://bucket-name/path/to/file)",
        widget=forms.TextInput(attrs={"class": "govuk-input"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate the endpoint choices dynamically from settings
        self.fields["s3_endpoint"].choices = [
            (endpoint_key, endpoint_key.replace("_", " ").title())
            for endpoint_key in settings.S3_ENDPOINTS.keys()
        ]

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "s3_endpoint", "s3_url", GovSubmit("submit", "Start Ingest")
        )
