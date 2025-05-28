from django.db.models import Func
from django.db.models import BooleanField


class SqlServerIsValidDecimal(Func):
    """
    Custom function to check if a field can be parsed as a decimal with specified precision.
    Used in annotations to validate decimal string fields.
    """
    output_field = BooleanField()

    def __init__(self, expression, max_digits=10, decimal_places=2, **kwargs):
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        super().__init__(expression, **kwargs)

    def as_sql(self, compiler, connection):
        expression_sql, params = compiler.compile(self.source_expressions[0])

        # Calculate the maximum absolute value based on precision
        max_value = 10 ** (self.max_digits - self.decimal_places)

        sql = (
            f"CASE WHEN TRY_CONVERT(DECIMAL({self.max_digits},{self.decimal_places}), "
            f"{expression_sql}) IS NOT NULL THEN 1 ELSE 0 END"
        )

        return sql, params


class SqlServerIsValidDecimalOrNull(SqlServerIsValidDecimal):
    """
    Custom function to check if a field is NULL or can be parsed as decimal with specified precision.
    """

    def as_sql(self, compiler, connection):
        expression_sql, params = compiler.compile(self.source_expressions[0])

        max_value = 10 ** (self.max_digits - self.decimal_places)

        sql = (
            f"CASE WHEN {expression_sql} IS NULL THEN 1 "
            f"WHEN TRY_CONVERT(DECIMAL({self.max_digits},{self.decimal_places}), "
            f"{expression_sql}) IS NOT NULL THEN 1 ELSE 0 END"
        )

        return sql, params
