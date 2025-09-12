from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field
from crispy_forms.layout import Layout
from crispy_forms.layout import Submit
from django import forms


class JobAdvertForm(forms.Form):
    job_description = forms.CharField(
        label="Job Description",
        max_length=4096,
        widget=forms.Textarea(attrs={"placeholder": "Enter job description"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Field(
                "job_description",
                css_class="form-control",
                placeholder="Enter job description",
            ),
            Submit("submit", "Process Description", css_class="govuk-button"),
        )
