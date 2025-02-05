# schemas/user.py
from pydantic import BaseModel, EmailStr, constr, validator
from typing import Optional,Union, Dict
from datetime import datetime
import re




# User Requests
class UserRegisterRequest(BaseModel):
    firstname: constr(min_length=2, max_length=50, strip_whitespace=True)
    lastname: constr(min_length=1, max_length=50, strip_whitespace=True)
    email: EmailStr
    # password: constr(min_length=8, max_length=50)
    role: Optional[str] = "USER"
    recaptcha: str

    @validator('firstname', 'lastname')
    def validate_name(cls, v):
        if not v.replace(' ', '').isalpha():
            raise ValueError('Name must contain only letters')
        return v.title()

    @validator('role')
    def validate_role(cls, v):
        valid_roles = ['USER', 'ADMIN']
        if v.upper() not in valid_roles:
            raise ValueError('Invalid role')
        return v.upper()
    

class EmailVerificationRequest(BaseModel):
    email: EmailStr
    verification_code: constr(min_length=6, max_length=6)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    recaptcha: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class EmailOnlyLoginRequest(BaseModel):
    email: EmailStr
    recaptcha: str

class EmailLoginVerificationRequest(BaseModel):
    email: EmailStr
    verification_code: constr(min_length=6, max_length=6)

class GoogleAuthRequest(BaseModel):
    token: str



# User Responses

class StandardResponse(BaseModel):
    status: bool
    message: str
    # data: Optional[dict] = None
    data: Optional[Union[Dict, str]] = None


class AuthResponse(BaseModel):
    access_token: str
    access_token_expires_time: datetime
    refresh_token: str
    refresh_token_expires_time: datetime

class UserInfo(BaseModel):
    firstname: str
    lastname: str
    email: str
    role: str

class LoginResponse(BaseModel):
    auth: AuthResponse
    userinfo: UserInfo


class GoogleUserInfo(BaseModel):
    email: EmailStr
    given_name: str
    family_name: str