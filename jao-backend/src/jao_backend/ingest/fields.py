from django import forms
from s3_parse_url import UnsupportedStorage
from s3_parse_url import parse_s3_url


class S3URLField(forms.CharField):
    """Custom field that validates S3 URLs (s3://bucket-name/path/to/file)"""

    def validate(self, value):
        super().validate(value)

        try:
            parse_s3_url(value)
        except ValueError as e:
            raise forms.ValidationError(f"Invalid S3 URL: {str(e)}")
        except UnsupportedStorage as e:
            raise forms.ValidationError(f"Unsupported storage type: {str(e)}")
