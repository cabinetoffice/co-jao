import json
import logging
from typing import Any, Dict

from django.http import JsonResponse
from jao_backend_schemas.vacancies import LintRequest
from jao_backend_schemas.vacancies import LintResponse
from ninja import NinjaAPI
from ninja.parser import Parser
from ninja.router import Router
from recruitmentcopilot.text.services import LintingService

from jao_backend.api.auth import ApiKeyAuth

logger = logging.getLogger(__name__)


router, common_router = Router()


class CustomParser(Parser):
    """
    Custom parser to handle JSON requests with UTF-8 encoding
    """

    def parse(self, request):
        try:
            return json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            raise


@common_router.get("/hello")
def hello(request) -> Dict[str, str]:
    """Basic greeting endpoint compatibility check"""
    return {"message": "Hello World"}


@common_router.get("/health")
def health_check(request) -> Dict[str, Any]:
    """
    Health check endpoint for load balancers and monitoring.
    """
    return {"status": "healthy", "service": "jao-backend-api", "version": "1.0.0", "checks_available": list(LintingService().available_checks.keys())}

@router.post("/lint", auth=ApiKeyAuth(), response=LintResponse)
def lint_text(request, payload: LintRequest):
    """
    Unified linting endpoint API handler for various checks

    Args:
        request: The HTTP request object
        text: The text to be linted.
        checks: Optional list of check types to perform

    Returns:
        Response containing:
            - source_text: The original text
            - issues: List of linting issues found
            - metadata: Summary information including:
                - total_issues: Count of issues found
                - checks_performed: List of executed checks
                - validations: Overall validation status (True, if no issues)
    """

    # Initialise service and process
    try:
        service = LintingService()
        issues = service.lint(text=payload.text, check_types=payload.check_types)

        logger.debug(
            f"Linting text: {payload.text[:200]}... with checks: {payload.check_types}"
        )
        logger.debug(f"Found issues: {issues}")

        # Build checker name mapping
        checker_names = {
            "acronym": "AcronymHybridChecker",
            "salary": "SalaryHybridChecker",
            "list_format": "ListFormatHybridChecker",
        }

        result = {
            "issues": issues,
            "source_text": payload.text,
            "meta": {
                "checks_performed": [
                    {
                        "type": check_type,
                        "verified": True,  # Always True since we performed the check
                        "valid": not any(
                            i["checker"] == checker_names[check_type] for i in issues
                        ),
                        "issues_found": sum(
                            1
                            for i in issues
                            if i["checker"] == checker_names[check_type]
                        ),
                    }
                    for check_type in payload.check_types
                ],
                "chars_processed": len(payload.text),
            },
        }
        return JsonResponse(
            result,
            json_dumps_params={"ensure_ascii": False},
            content_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.exception("Linting failed")
        return JsonResponse(
            {"error": "Internal server error"},
            status=500,
            content_type="application/json; charset=utf-8",
        )


# @router.post("/lint-stub", auth=ApiKeyAuth())
def lint_stub(request, payload: LintRequest):
    #     """
    #     Temporary endpoint for unblocking frontend work

    #     Features:
    #         Uses fully immutable core
    #         Return sample issues for all check types
    #         Bypasses complex validation
    #     """
    pass


api = NinjaAPI(
    title="JAO Backend API",
    version="1.0.0",
    urls_namespace="lint_api",
    csrf=False,
)


api.add_router("", router)
api.add_router("", common_router)

__all__ = ["api", "router"]
