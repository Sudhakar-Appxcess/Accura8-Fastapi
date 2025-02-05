# exceptions/code_converter_exceptions.py
class APIKeyNotFoundError(Exception):
    """Raised when the Gemini API key is missing"""
    def __init__(self, message="Gemini API key not found"):
        self.message = message
        super().__init__(self.message)

class ModelNotAvailableError(Exception):
    """Raised when the Gemini model is not available"""
    def __init__(self, message="Gemini model is not available"):
        self.message = message
        super().__init__(self.message)

class InvalidRequestError(Exception):
    """Raised when the conversion request is invalid"""
    def __init__(self, message="Invalid code conversion request"):
        self.message = message
        super().__init__(self.message)

class ConversionError(Exception):
    """Raised when code conversion fails"""
    def __init__(self, message="Code conversion failed"):
        self.message = message
        super().__init__(self.message)

class MigrationError(Exception):
    """Raised when SQL migration fails"""
    def __init__(self, message="SQL migration failed", data=None):
        self.message = message
        self.status_code = 422
        self.data = data or {}
        super().__init__(self.message)