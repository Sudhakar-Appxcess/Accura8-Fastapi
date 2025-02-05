class NLToSQLError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class SchemaError(NLToSQLError):
    def __init__(self, message: str = "Invalid database schema provided"):
        super().__init__(message=message, status_code=400)