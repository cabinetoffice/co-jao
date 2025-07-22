import re
from typing import Dict
from typing import Generator
from typing import List

from jao_backend.text.checker.acronym import AcronymHybridChecker

# from jao_backend.text.checkers import AcronymHybridChecker
from jao_backend.text.checker.list_format import ListFormatHybridChecker
from jao_backend.text.textspan import TextSpan


class LintingService:
    def __init__(self):
        self.available_checks = {
            "acronym": AcronymHybridChecker,
            "list_format": ListFormatHybridChecker,
        }

    def lint(self, text: str, check_types: List[str] = None) -> List[Dict]:
        """Main entry point for linting checks"""
        if not check_types:
            raise ValueError("At least one check type must be specified")

        if "all" in check_types:
            checkers = self.available_checks.items()
        else:
            self._validate_check_types(check_types)
            checkers = (
                (k, v) for k, v in self.available_checks.items() if k in check_types
            )

        return list(self._run_checks(text, checkers))

    def _validate_check_types(self, check_types: List[str]):
        """Ensure requested check types are valid"""
        invalid = set(check_types) - set(self.available_checks.keys())
        if invalid:
            raise ValueError(
                f"Invalid check types: {invalid}. "
                f"Available: {list(self.available_checks.keys())}"
            )

    def _run_checks(self, text: str, checkers) -> Generator[Dict, None, None]:
        """Execute all requested checks"""
        doc_span = TextSpan(source_text=text, start_index=0, end_index=len(text))

        for check_name, checker_cls in checkers:
            checker = checker_cls(doc_span)
            yield from (issue.to_dict() for issue in checker.check(doc_span))
