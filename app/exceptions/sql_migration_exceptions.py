
# exceptions/sql_migration_exceptions.py
class SQLMigrationError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class InvalidSQLError(SQLMigrationError):
    def __init__(self, message: str = "Invalid SQL query"):
        super().__init__(message=message, status_code=400)

class UnsupportedFeatureError(SQLMigrationError):
    def __init__(self, message: str = "Unsupported database feature"):
        super().__init__(message=message, status_code=400)