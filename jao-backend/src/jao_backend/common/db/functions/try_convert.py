from django.db.models import Func

"""
TRY_CONVERT is a SQL Server specific function to attempt to convert an expression to a specified data type.

https://learn.microsoft.com/en-us/sql/t-sql/functions/try-convert-transact-sql?view=sql-server-ver17
"""


class TryConvert(Func):
    """
    SQL Server specific TRY_CONVERT as a Func.
    """

    function = "TRY_CONVERT"

    def __init__(self, target_field, expression, **kwargs):
        self.target_field = target_field
        super().__init__(expression, **kwargs)

    def as_sql(self, compiler, connection, **kwargs):
        target_type_sql = self.target_field.db_type(connection)
        expression_sql, params = compiler.compile(self.source_expressions[0])
        sql = f"TRY_CONVERT({target_type_sql}, {expression_sql})"
        return sql, params
