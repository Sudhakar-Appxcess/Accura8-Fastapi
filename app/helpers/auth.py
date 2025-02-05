# helpers/auth.py
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.db import get_db
from app.models.user import Guest
from app.exceptions.custom_exceptions import CustomException
from logzero import logger
import jwt
from app.config import settings
from app.helpers.ip import get_system_ip

class OptionalHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        try:
            return await super().__call__(request)
        except HTTPException:
            return None

optional_security = OptionalHTTPBearer(auto_error=False)
strict_security = HTTPBearer()

class AuthMiddleware:
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = "HS256"

    async def handle_guest(self, request: Request, db: Session) -> dict:
        """Handle guest user tracking and credits using system IP"""
        ip_address = get_system_ip()  # Get actual system IP
        guest = db.query(Guest).filter(Guest.ip_address == ip_address).first()
        
        if not guest:
            guest = Guest(ip_address=ip_address)
            db.add(guest)
            db.commit()
        
        return {
            "authenticated": False,
            "guest_data": {
                "ip_address": ip_address,
                "credits_remaining": guest.credit_balance
            }
        }

    async def verify_token(self, token: str) -> dict:
        """Verify JWT token and return user data"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if not payload:
                raise CustomException(message="Invalid token")
            return payload
        except jwt.ExpiredSignatureError:
            raise CustomException(message="Token has expired")
        except jwt.JWTError as e:
            raise CustomException(message=f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            raise CustomException(message="Token verification failed")

    async def get_optional_auth(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
        db: Session = Depends(get_db)
    ) -> dict:
        """Optional authentication middleware"""
        try:
            if credentials and credentials.credentials:
                user_data = await self.verify_token(credentials.credentials)
                return {
                    "authenticated": True,
                    "user_data": user_data
                }
        except Exception as e:
            logger.warning(f"Token verification failed: {str(e)}")
        
        return await self.handle_guest(request, db)

    async def get_strict_auth(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(strict_security)
    ) -> dict:
        """Strict authentication middleware"""
        try:
            user_data = await self.verify_token(credentials.credentials)
            return user_data
        except CustomException as ce:
            raise HTTPException(status_code=401, detail=ce.message)
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# Create singleton instance
auth_handler = AuthMiddleware()

# Convenience decorators for routes
optional_auth = auth_handler.get_optional_auth
strict_auth = auth_handler.get_strict_auth