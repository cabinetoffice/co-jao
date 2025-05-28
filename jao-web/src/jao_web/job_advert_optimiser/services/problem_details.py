import json
import logging
from typing import List, Optional

from django.conf import settings
from django.http import Http404

from pydantic import BaseModel, ValidationError

from jao_web.job_advert_optimiser.services.helpers import success_or_redirect

logger = logging.getLogger(__name__)


class TracebackFrame(BaseModel):
    filename: str
    lineno: int
    name: str
    line: str


class TracebackDetails(BaseModel):
    exc_type: str
    exc_message: str
    stack: List[TracebackFrame]


class ProblemDetails(BaseModel):
    """RFC 9457 Problem Details."""

    type: Optional[str] = "about:blank"
    """Problem type URI."""

    title: Optional[str] = None
    """Short summary of the problem type."""

    status: int
    """HTTP status code."""

    detail: Optional[str] = None
    """Specific explanation of the problem."""

    instance: Optional[str] = None
    """Problem occurrence URI."""

    traceback: Optional[TracebackDetails] = None
    """Stack trace (if include_stacktrace was True)."""

    code: Optional[str] = None
    """Application-specific error code."""


class ServiceProblem(Exception):
    """
    RFC 9457 Problem details from a service response.
    """

    def __init__(self, problem_details):
        if isinstance(problem_details, str):
            try:
                # Try to parse as JSON
                problem_details = ProblemDetails.parse_raw(problem_details)
            except ValidationError as e:
                if settings.DEBUG:
                    raise

                logger.error(
                    "Could not parse problem details: %s %s", problem_details, e
                )
                raise e

        if not isinstance(problem_details, ProblemDetails):
            if settings.DEBUG:
                raise

            raise ValueError(
                "problem_details must be a ProblemDetails instance or a valid JSON"
                f" string representation, not a {type(problem_details).__name__}."
            )

        self.problem_details = problem_details
        super().__init__(self.format_message())

    def format_message(self):
        message = (
            f"Problem Type: {self.problem_details.type}\n"
            f"Title: {self.problem_details.title}\n"
            f"Status: {self.problem_details.status}\n"
            f"Detail: {self.problem_details.detail}\n"
            f"Instance: {self.problem_details.instance}\n"
            f"Code: {self.problem_details.code}\n"
        )
        if settings.DEBUG and self.problem_details.traceback:
            message += f"Traceback:\n{self.problem_details.traceback}"
        return message

    def __reduce__(self):
        return self.__class__, (self.problem_details.json(),)

    @staticmethod
    def raise_from_response(response, response_ok=success_or_redirect):
        if response_ok(response.status_code):
            return

        logger.error(
            "HTTP %s: %s, calling %s",
            response.status_code,
            response.text,
            response.request.url,
        )
        if response.status_code in [404]:
            logger.error(response.text)
            if settings.DEBUG:
                msg = f"Resource not found {response.request.url}.  {response.text}"
            else:
                msg = "Resource not found"
            raise Http404(msg)
        try:
            # The response could be a problem details object
            problem_details = ProblemDetails.model_validate(response.json())
            problem = ServiceProblem(problem_details)
            logger.error(f"Service problem: {problem}")
            raise problem
        except (ValidationError, json.JSONDecodeError):
            if response.status_code in [404]:
                raise ValueError("Resource not found") from None
        except Exception as e:
            logger.error(
                f"Error parsing problem details: {e}\n response: {response.text},"
                f" DEBUG: {settings.DEBUG}"
            )
            if settings.DEBUG:
                raise

            raise ValueError("Error parsing problem details") from e


def raise_exception_on_problem(response, response_ok=success_or_redirect):
    if response_ok(response.status_code):
        logger.info(
            "Response [%s]: %s", response.status_code, response.request.url
        )
        return

    logger.error(
        "Unexpected Response [%s]: %s", response.status_code, response.request.url
    )
    ServiceProblem.raise_from_response(response, response_ok=success_or_redirect)
    raise ValueError(response.text)
