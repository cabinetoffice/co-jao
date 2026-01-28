import logging

from django.db.utils import OperationalError
from django.db.utils import ProgrammingError

try:
    from pyodbc import ProgrammingError as PyodbcProgrammingError
except ImportError:
    class PyodbcProgrammingError(Exception):
        pass

logger = logging.getLogger(__name__)


class DatabaseConnectionLostError(Exception):
    pass


def is_connection_error(exc) -> bool:
    if not exc.args:
        return False

    if (
            isinstance(exc, PyodbcProgrammingError) and
            exc.args == ("The cursor's connection has been closed.",)
    ):
        return True

    code = str(exc.args[0])
    return code.startswith("08")
