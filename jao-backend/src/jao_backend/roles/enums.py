from enum import Enum


class GradeType(Enum):
    """Enumeration of civil service grades."""

    AA = (1, "Administrative Assistant", "AA")
    AO = (2, "Administrative Officer", "AO")
    EO = (3, "Executive Officer", "EO")
    HEO = (4, "Higher Executive Officer", "HEO")
    SEO = (5, "Senior Executive Officer", "SEO")
    G7 = (6, "Grade 7", "G7")
    G6 = (7, "Grade 6", "G6")
    SCS1 = (8, "Senior Civil Service 1", "SCS1")
    SCS2 = (9, "Senior Civil Service 2", "SCS2")
    SCS3 = (10, "Senior Civil Service 3", "SCS3")
    SCS4 = (11, "Senior Civil Service 4", "SCS4")

    def __init__(self, numeric_value, long_name, short_name):
        self.numeric_value = numeric_value
        self.long_name = long_name
        self.short_name = short_name

    @classmethod
    def from_name(cls, name):
        """Get a GradeType from its name."""
        for grade in cls:
            if grade.short_name == name:
                return grade
        raise ValueError(f"No grade found with name {name}")

    @classmethod
    def choices(cls):
        """Return choices for Django model field."""
        return [(grade.short_name, grade.long_name) for grade in cls]
