from django.db import models

# Create your models here.
class ListModel(models.Model):
    """
    Base model for lists - these originate in OLEEO/R2D2 and are reflected in JAO.

    This model contains the fields common to all list models.

    In JAO the fields are named using Django conventions.
    """

    id = models.AutoField(primary_key=True)
    """Primary key, as imported from oleoo r2dr"""
    description = models.TextField()

    last_updated = models.DateTimeField()

    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def __str__(self):
        return self.description

    def __repr__(self):
        return f"<{type(self).__name__} description='{self.description}>'"


class ProtectedCharacteristicList(ListModel):
    """Abstract base class for all protected characteristic mixins"""

    # Using a class like this makes it possible to iterate through only
    # the protected characteristic mixins when needed.
    class Meta:
        abstract = True
