from cachemethod import lru_cachemethod
from django.contrib.postgres.fields import ArrayField
from django.db import models

from jao_backend.common.db.models.models import ListModel
from jao_backend.common.db.models.models import ProtectedCharacteristicList
from jao_backend.oleeo.base_models import UpstreamModelMixin
from jao_backend.roles.querysets import OleeoGradeGroupQuerySet
from jao_backend.roles.querysets import OleeoRoleTypeGroupQuerySet


class RoleType(ListModel):
    """Role types JAO stores aggregated data about."""


class Grade(ProtectedCharacteristicList):
    """Job grades JAO stores aggregated data about."""

    shorthand_name = models.TextField(unique=True)

    ingest_unique_id_field = "shorthand_name"

    class Meta:
        ordering = ["description"]

    def __repr__(self):
        return (
            f"<{type(self).__name__} shorthand_name='{self.shorthand_name}',"
            f" description='{self.description}'>"
        )


class OleeoGradeGroup(ListModel, UpstreamModelMixin):
    """Oleeo groups grades together in comma seperated lists.

    JAO syncs them to here before exploding the data into individual grades.

    Only used during ingest, JAO django apps should not link to this model.
    """

    destination_model = "roles.Grade"
    ingest_last_updated_field = "last_updated"
    ingest_unique_id_field = "shorthand"
    """
    Grade is derived from OleeoGradeGroup, which contains a list of grade combinations,
    this is split up by finding the combinations that are only a single grade.
    """

    objects = models.Manager()
    """default manager"""

    objects_for_ingest = OleeoGradeGroupQuerySet.as_manager()
    """manager when this is being upstream to roles.Grade"""

    description = ArrayField(models.TextField(), size=None, default=list)

    shorthand = ArrayField(models.TextField(), size=None, default=list)

    @lru_cachemethod(maxsize=1)
    def get_grades(self):
        """Return the grades in the shorthand list."""
        return Grade.objects.filter(shorthand_name__in=self.shorthand)

    def __repr__(self):
        return f"<{type(self).__name__} description={self.description}>"

    class Meta:
        verbose_name_plural = "OLEEO role groups"
        ordering = ["description"]


class OleeoRoleTypeGroup(ListModel, UpstreamModelMixin):
    """OLEEO stores roles grouped in comma seperated lists

    JAO syncs them here before exploding the data into individual role typs.

    Only used during ingest, JAO django apps should not link to this model.
    """

    objects = models.Manager()
    """default manager"""

    objects_for_ingest = OleeoRoleTypeGroupQuerySet.as_manager()
    """manager when this is being upstream to roles.RoleType"""

    destination_model = "roles.RoleType"
    ingest_last_updated_field = "last_updated"

    description = ArrayField(models.TextField(), size=None, default=list)

    @lru_cachemethod(maxsize=1)
    def get_role_types(self):
        """Return the grades in the shorthand list."""
        return RoleType.objects.filter(description__in=self.description)

    def __repr__(self):
        return f"<{type(self).__name__} description='{self.description}'>"
