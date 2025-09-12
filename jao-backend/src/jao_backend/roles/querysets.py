from jao_backend.oleeo.querysets import UpstreamModelQuerySet


class OleeoGradeGroupQuerySet(UpstreamModelQuerySet):

    def valid_for_ingest(self):
        """Get only the valid OleeoGradeGroup objects that have a single grade within the shorthand list."""
        return self.extra(
            select={
                "grade_shorthand": "unnest(shorthand)",
                "position": "generate_subscripts(shorthand, 1)",
            },
            where=["array_length(shorthand, 1) = 1"],
        )


class OleeoRoleTypeGroupQuerySet(UpstreamModelQuerySet):

    def valid_for_ingest(self):
        """Get only the valid OleeoRoleTypeGroup objects that have a single grade within the shorthand list."""
        return self.extra(
            select={
                "role_description": "unnest(description)",
                "position": "generate_subscripts(description, 1)",
            },
            where=["array_length(description, 1) = 1"],
        )
