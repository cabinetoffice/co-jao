from typing import Dict, List, Any, Dict, Field, Tuple, Optional

from pydantic import BaseModel, Field, model_validator


class JobDescriptionRequest(BaseModel):
    description: str


class JobDescriptionOptimisationRequest(JobDescriptionRequest):
    pass


class VacancyListing(BaseModel):
    job_title: str
    full_job_desc: str
    vacancy_id: int


class SimilarVacanciesResponse(BaseModel):
    similar_vacancies: List[VacancyListing]

class LintIssue(BaseModel):
    """
    An individual linting issue

    Attributes:
        type: Checker class name
        description: Human-readable issue description
        span: Tuple of (start, end) indices for the issue in the text
        highlight: List of relevant text spans
    """

    type: str
    description: str
    span: Tuple[int, int]
    highlight: List[Tuple[int, int]]


class LintResponse(BaseModel):
    """Schema for linting response"""

    source_text: str = Field(default="", min_length=0)
    issues: List[Dict[str, Any]]
    meta: Dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata container"
    )


class TextInput(BaseModel):
    """Schema for text input validation requests"""

    text: str
    style: str = "content"  # Default to content-style-01

class SalaryValidationResponse(BaseModel):
    """API response schema for salary validation

    Attributes:
        source_text: Original input text
        issues: List of detected issues
        valid: Whether the salary format is valid
    """

    source_text: str
    issues: List[LintIssue]
    valid: bool


class SalaryConfig(BaseModel):
    """Configuration options for salary checks"""

    allow_k_notation: bool = True
    require_commas: bool = False


class AcronymConfig(BaseModel):
    """Configuration options for acronym checks"""

    ignore_list: List[str] = []


class ListFormatConfig(BaseModel):
    """Configuration options for list format checks"""

    require_period: bool = True


class LintConfig(BaseModel):
    """Configuration for all check types"""

    salary: Optional[SalaryConfig] = None
    acronyms: Optional[AcronymConfig] = None
    list_format: Optional[ListFormatConfig] = None


class LintRequest(BaseModel):
    """Schema for linting requests"""

    text: str
    # checks: List[str] = []
    check_types: List[str] = Field(default=["all"], alias="checks")
    config: Optional[LintConfig] = None

    @model_validator(mode="before")
    def handle_legacy_check_types(cls, values):
        """Convert legacy 'checks' field to 'check_types'"""
        if "check_types" in values and "checks" not in values:
            values["checks"] = values.pop("check_types")

        return values
