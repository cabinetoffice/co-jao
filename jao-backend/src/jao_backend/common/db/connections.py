import logging
import wrapt

from django.db import connections
from django.db.utils import OperationalError
from django.db.utils import ProgrammingError

try:
    # Don't on environments not using pyodbc.
    from pyodbc import ProgrammingError as PyodbcProgrammingError
except ImportError:
    class PyodbcProgrammingError(Exception):
        # Dummy class if pyodbc is not installed
        pass

logger = logging.getLogger(__name__)

disconnection_count = 0

class DatabaseConnectionLostError(Exception):
    """Raised when the database connection is lost (VPN, network, or server issue)."""
    pass


def is_connection_error(exc) -> bool:
    """
    Detect if an OperationalError represents a lost DB connection.

    Uses SQLSTATE Class 08 — Connection Exception (ISO/ANSI SQL standard):
    https://en.wikipedia.org/wiki/SQLSTATE

    SQL Server: https://learn.microsoft.com/en-us/sql/odbc/reference/appendixes/appendix-a-odbc-error-codes?view=sql-server-ver15
    PostgreSQL: https://www.postgresql.org/docs/current/errcodes-appendix.html

    Common codes:
      08000 - Connection exception
      08001 - SQL-client unable to establish SQL-connection
      08003 - Connection does not exist
      08004 - SQL-server rejected establishment of SQL-connection
      08006 - Connection failure
      08007 - Connection failure during transaction
      08S01 - Communication link failure
    """
    if not exc.args:
        return False

    if (
            isinstance(exc, PyodbcProgrammingError) and
            exc.args == ("The cursor's connection has been closed.",)
    ):
        return True

    code = str(exc.args[0])
    return code.startswith("08")

def _translate_disconnect_exception(exc) -> Exception:
    global disconnection_count
    if isinstance(exc, (OperationalError, ProgrammingError, PyodbcProgrammingError)):
        if is_connection_error(exc):
            return DatabaseConnectionLostError(f"DB connection lost: {str(exc)}")

        if disconnection_count and isinstance(exc, OperationalError) and exc.args and exc.args[0] == 'HYT00':
            # Only check for disconnections if we were previously connected.
            # ('HYT00', '[HYT00] [Microsoft][ODBC Driver 17 for SQL Server]Login timeout expired (0) (SQLDriverConnect)')
            return DatabaseConnectionLostError(exc.args)

    if disconnection_count:
        # Reset the flag after one successful operation
        disconnection_count = False
    return exc

def on_db_disconnect_raise(using="default"):
    global disconnection_count

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        global disconnection_count
        try:
            logger.warning("Using DB connection '%s' for function '%s'", using, wrapped.__name__)
            return wrapped(*args, **kwargs)
        except Exception as e:
            translated_exception = _translate_disconnect_exception(e)
            if not isinstance(translated_exception, DatabaseConnectionLostError):
                logger.error("Non disconnection Exception in function '%s': %s", wrapped.__name__, e)
                raise

            logger.warning("Closing all %s connection [%s] due to %s disconnect.", using, e)
            disconnection_count += 1
            try:
                connections[using].close()
            except Exception as close_exc:
                logger.error("Error while closing DB connection [%s]: %s", using, close_exc)
            logger.warning("Database connection lost detected in function '%s': %s", wrapped.__name__, e)
            raise translated_exception from e

    return wrapper
