# exceptions/custom_exceptions.py
from typing import Optional

class CustomException(Exception):
    def __init__(self, message: str, status_code: int = 400, data: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(self.message)    

class UserExistsNotVerifiedError(CustomException):
    def __init__(self, message: str = "Email already registered, please verify your email!"):  
        super().__init__(message=message, status_code=409) 

class UserAlreadyExistsError(CustomException):
    def __init__(self, message: str = "Email already registered"):  
        super().__init__(message=message, status_code=400)  

class InvalidVerificationCodeError(CustomException):
    def __init__(self, message: str = "Invalid verification code or email"):
        super().__init__(message=message, status_code=400)

class VerificationCodeExpiredError(CustomException):
    def __init__(self, message: str = "Verification code has expired. Please request a new code."):
        super().__init__(message=message, status_code=400)

class InvalidCredentialsError(CustomException):
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message=message, status_code=401)

class UserNotVerifiedError(CustomException):
    def __init__(self, message: str = "Please verify your email before logging in"):
        super().__init__(message=message, status_code=403)

class UserNotActiveError(CustomException):
    def __init__(self, message: str = "Your account is not active"):
        super().__init__(message=message, status_code=403)

class ClientNotFoundError(CustomException):
    def __init__(self, message: str = "Client configuration not found"):
        super().__init__(message=message, status_code=500)

class UserAlreadyVerifiedError(CustomException):
    def __init__(self, message: str = "User is already verified"):
        super().__init__(message=message, status_code=400)

class NoVerificationPendingError(CustomException):
    def __init__(self, message: str = "No verification is pending for this user"):
        super().__init__(message=message, status_code=400)

class UserNotFoundError(CustomException):
    def __init__(self, message: str = "User not found"):
        super().__init__(message=message, status_code=404)