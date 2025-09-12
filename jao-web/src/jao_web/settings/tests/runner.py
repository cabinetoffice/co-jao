import pytest


class PytestTestRunner:
    """Runs pytest to discover and run tests."""

    def __init__(self, verbosity=1, failfast=False, keepdb=False, **kwargs):
        self.verbosity = verbosity
        self.failfast = failfast
        self.keepdb = keepdb

    def _get_pytest_argv(self, test_labels):
        """
        Construct the argv list for pytest based on the provided options
        """
        argv = []
        if self.verbosity == 0:
            argv.append("--quiet")
        if self.verbosity == 2:
            argv.append("--verbose")
        if self.verbosity == 3:
            argv.append("-vv")
        if self.failfast:
            argv.append("--exitfirst")
        if self.keepdb:
            argv.append("--reuse-db")

        argv.extend(test_labels)
        return argv

    def run_tests(self, test_labels):
        """
        Run pytest and return the exitcode
        """
        argv = self._get_pytest_argv(test_labels)
        return pytest.main(argv)
