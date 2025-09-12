from django import forms


class LiteLLMEmbeddingTestForm(forms.Form):
    """
    A form for testing LiteLLM embedding generation in the admin.
    """

    model = forms.CharField(
        label="LiteLLM Model",
        required=True,
        help_text="e.g., 'nomic-embed-text:latest' or 'sentence-transformers/all-MiniLM-L6-v2'",
        widget=forms.TextInput(attrs={"class": "vTextField", "size": "60"}),
        initial="sentence-transformers/all-MiniLM-L6-v2",
    )
    text = forms.CharField(
        label="Text to Embed",
        required=True,
        widget=forms.Textarea(attrs={"class": "vLargeTextField", "rows": 5}),
        initial="This is a test of the LiteLLM embedding service.",
    )
