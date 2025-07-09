from django.db.models import BooleanField
from django.db.models import Case
from django.db.models import DecimalField
from django.db.models import Func
from django.db.models import Value
from django.db.models import When
from django.db.models.lookups import IsNull
from django.db.models.lookups import Regex

from jao_backend.common.db.functions.try_convert import TryConvert


class IsValidDecimal(Func):
    """
    Check if a field can be parsed as a decimal with specified precision.
    Uses SQL Server TRY_CONVERT on SQL Server, regex on other databases.
    """

    output_field = BooleanField()

    def __init__(self, expression, max_digits=10, decimal_places=2, **kwargs):
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        super().__init__(expression, **kwargs)

    def _as_expr(self, compiler, connection):
        """
        Return a Django expression to check if a field can be parsed as a decimal.
        Uses TRY_CONVERT for SQL Server, regex for other databases.
        """
        if connection.vendor == "microsoft":
            return self._as_expr_try_convert(compiler, connection)

        return self._as_expr_regex(compiler, connection)

    def as_sql(self, compiler, connection, **kwargs):
        expr = self._as_expr(compiler, connection)
        return expr.as_sql(compiler, connection, **kwargs)

    def _as_expr_try_convert(self, compiler, connection, *extra_conditions):
        """
        Return a Django expression to check if a field can be parsed as a decimal.

        SQL Server implementation using TRY_CONVERT.

        Regex support is available from SQL Server 2025 (17.x) Preview,
        at the time of writing this is too new for most environments.

        This uses TRY_CONVERT, a SQLServer specific function.

        https://learn.microsoft.com/en-us/sql/t-sql/functions/try-convert-transact-sql?view=sql-server-ver17
        """

        # Create a DecimalField to get proper SQL type
        decimal_field = DecimalField(
            max_digits=self.max_digits, decimal_places=self.decimal_places
        )
        try_convert = TryConvert(decimal_field, self.source_expressions[0])

        return Case(
            *extra_conditions,
            When(condition=IsNull(try_convert, False), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )

    def _as_expr_regex(self, compiler, connection, *extra_conditions):
        """
        :return : Expression to check if a field can be parsed as a decimal using regex.
        """
        integer_digits = self.max_digits - self.decimal_places
        pattern = (
            f"^[+-]?\\d{{0,{integer_digits}}}(\\.\\d{{0,{self.decimal_places}}})?$"
            if self.decimal_places > 0
            else f"^[+-]?\\d{{1,{integer_digits}}}$"
        )

        return Case(
            *extra_conditions,
            When(
                condition=Regex(self.source_expressions[0], pattern), then=Value(True)
            ),
            default=Value(False),
            output_field=BooleanField(),
        )


class IsValidDecimalOrNull(IsValidDecimal):
    """
    Check if a field can be parsed as a decimal with specified precision or is Null.
    Uses SQL Server TRY_CONVERT on SQL Server, regex on other databases.
    """

    def _as_expr_try_convert(self, compiler, connection, *extra_conditions):
        null_check = When(
            condition=IsNull(self.source_expressions[0], True), then=Value(True)
        )
        return super()._as_expr_try_convert(
            compiler, connection, null_check, *extra_conditions
        )

    def _as_expr_regex(self, compiler, connection, *extra_conditions):
        null_check = When(
            condition=IsNull(self.source_expressions[0], True), then=Value(True)
        )
        return super()._as_expr_regex(
            compiler, connection, null_check, *extra_conditions
        )
