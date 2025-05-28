from django.db import models
from jao_backend.common.fields import UUIDField


class Department(models.Model):
    id = UUIDField(primary_key=True, editable=False, version=7)
    name = models.CharField(max_length=100)
    description = models.TextField()
