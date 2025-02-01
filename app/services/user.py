# services/user.py
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from logzero import logger
from typing import Tuple
from typing import Tuple, Dict
import os
import aiohttp
import json
from app.models.user import User, Role, AccessToken, RefreshToken, Client
from app.helpers.password import hash_password
from app.services.email import generate_verification_code, send_verification_email
from app.schemas.user import UserRegisterRequest,StandardResponse
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from jose import JWTError, jwt
import uuid
from app.config import settings
import pytz 
from user_agents import parse
import bcrypt
from app.exceptions.custom_exceptions import (
    InvalidVerificationCodeError,
    VerificationCodeExpiredError,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    UserNotVerifiedError,
    UserNotActiveError,
    ClientNotFoundError,
    NoVerificationPendingError,
    UserAlreadyVerifiedError,
    UserNotFoundError
)
class UserService:

    # fernet = Fernet(settings.FERNET_SECRET_KEY)
    fernet_key = Fernet.generate_key()  # Generate the key
    _fernet = Fernet(fernet_key)        # Create Fernet instance

    GOOGLE_TOKEN_VERIFY_URL = "https://oauth2.googleapis.com/tokeninfo"
    
    
    @classmethod
    def encrypt_data(cls, data: dict) -> str:
        return cls._fernet.encrypt(json.dumps(data).encode()).decode()

    @staticmethod
    async def register_user(db: Session, user_data: UserRegisterRequest):
        logger.info(f"Registration attempt for email: {user_data.email}")
        
        if db.query(User).filter(User.email == user_data.email).first():
            logger.warning(f"Registration failed - email already exists: {user_data.email}")
            raise UserAlreadyExistsError()

        try:
            # Try to find the requested role
            role = db.query(Role).filter(Role.name == user_data.role).first()
            
            if not role:
                logger.info(f"Requested role '{user_data.role}' not found, checking for USER role")
                # If requested role doesn't exist, try to find USER role
                role = db.query(Role).filter(Role.name == "USER").first()
                
                if not role:
                    # If USER role doesn't exist, create it
                    logger.info("Creating default USER role")
                    role = Role(
                        name="USER",
                        description="Default user role with basic privileges"
                    )
                    db.add(role)
                    db.flush()
                    logger.info(f"Created default USER role with id: {role.id}")
                else:
                    logger.info(f"Using existing USER role with id: {role.id}")
            else:
                logger.info(f"Using requested role '{role.name}' with id: {role.id}")

            verification_code = generate_verification_code()


            current_time = datetime.now(pytz.UTC)
            user = User(
                email=user_data.email,
                firstname=user_data.firstname,
                lastname=user_data.lastname,
                password=hash_password(user_data.password),
                role_id=role.id,
                verification_code=verification_code,
                verification_code_expires_at=current_time + timedelta(minutes=10)
            )
            #  Add user but don't commit yet
            db.add(user)
            db.flush()  # This gets us the user.id without committing

            try:
                # Try to send email
                await send_verification_email(user.email, verification_code)
                
                # If email sends successfully, commit the transaction
                db.commit()
                logger.info(f"User registered successfully: {user.email}")
                return user
                
            except Exception as email_error:
                # If email fails, rollback the user creation
                db.rollback()
                logger.error(f"Email sending failed, rolling back user creation: {str(email_error)}")
                raise Exception("Failed to send verification email") from email_error
                
        except Exception as e:
            db.rollback()
            logger.error(f"Registration failed: {str(e)}")
            raise


    @staticmethod
    async def verify_email(db: Session, email: str, verification_code: str):
        logger.info(f"Email verification attempt for: {email}")
        
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            logger.warning(f"Verification failed - user not found: {email}")
            raise InvalidVerificationCodeError()
            
        if user.is_verified:
            logger.info(f"User already verified: {email}")
            return InvalidVerificationCodeError("User is Already Verified")
            
        if not user.verification_code or user.verification_code != verification_code:
            logger.warning(f"Verification failed - invalid code for user: {email}")
            raise InvalidVerificationCodeError()
        
        # Convert current time to UTC for comparison
        current_time = datetime.now(pytz.UTC)
        if user.verification_code_expires_at < current_time:
            logger.warning(f"Verification failed - code expired for user: {email}")
            raise VerificationCodeExpiredError()
            
        try:
            # Update user verification status
            user.is_verified = True
            user.is_active = True
            user.verification_code = None
            user.verification_code_expires_at = None
            
            db.commit()
            logger.info(f"Email verified successfully for user: {email}")
            return user
            
        except Exception as e:
            db.rollback()
            logger.error(f"Email verification failed: {str(e)}")
            raise
    @staticmethod
    def _verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode(), 
            hashed_password.encode()
        )

    @staticmethod
    def _get_client_by_user_agent(db: Session, user_agent_string: str) -> Client:
        ua = parse(user_agent_string)
        
        if ua.is_mobile:
            if ua.os.family == 'iOS':
                client_id = 'IOS_GOOGLE_SSO'
            else:
                client_id = 'ANDROID_GOOGLE_SSO'
        else:
            client_id = 'WEB_GOOGLE_SSO'
            
        client = db.query(Client).filter(Client.client_id == client_id).first()
        if not client:
            logger.error(f"Client not found for {client_id}")
            raise ClientNotFoundError()
            
        return client

    @classmethod
    async def login(
        cls,
        db: Session,
        email: str,
        password: str,
        user_agent_string: str
    ) -> dict:
        logger.info(f"Login attempt for email: {email}")
        
        try:
            user = db.query(User).filter(User.email == email).first()

            if not user:
                logger.warning(f"User not found: {email}")
                raise InvalidCredentialsError()
            # In the login method, add this check:
            if not user.password:
                logger.warning(f"User {email} has no password set")
                raise InvalidCredentialsError("Invalid login method")

            if not cls._verify_password(password, user.password):
                logger.warning(f"Invalid credentials for email: {email}")
                raise InvalidCredentialsError()


            if not user.is_verified:
                logger.warning(f"Unverified user attempt to login: {email}")
                raise UserNotVerifiedError()

            if not user.is_active:
                logger.warning(f"Inactive user attempt to login: {email}")
                raise UserNotActiveError()

            # Get appropriate client based on user agent
            client = cls._get_client_by_user_agent(db, user_agent_string)
            
            # Generate tokens
            access_token, refresh_token = cls._generate_tokens(db, user, client)
            
            # Prepare response data
            auth_data = {
                "access_token": access_token.token,
                "access_token_expires_time": access_token.expires_at.isoformat(),
                "refresh_token": refresh_token.token,
                "refresh_token_expires_time": refresh_token.expires_at.isoformat()
            }
            
            user_info = {
                "firstname": user.firstname,
                "lastname": user.lastname,
                "email": user.email,
                "role": user.role.name
            }
            
            

            
            
            response_data = {
                "auth": auth_data,
                "userinfo": user_info
            }
            encrypted_data = cls.encrypt_data(response_data)

            # Commit the transaction
            db.commit()
            logger.info(f"Login successful for user: {email}")
            
            return {
                "status": True,
                "message": "Login successful",
                "data": encrypted_data
            }

        except (InvalidCredentialsError, UserNotVerifiedError, 
                UserNotActiveError, ClientNotFoundError) as e:
            raise
            
        except Exception as e:
            db.rollback()
            logger.error(f"Login failed: {str(e)}")
            raise

    @staticmethod
    def create_jwt_token(data: dict, expires_delta: timedelta) -> str:
        """
        Create a JWT token with given data and expiration using UTC time
        """
        to_encode = data.copy()
        current_utc = datetime.now(pytz.UTC)
        expire_utc = current_utc + expires_delta
        
        to_encode.update({
            "exp": int(expire_utc.timestamp()),  # UTC timestamp for JWT
            "iat": int(current_utc.timestamp())  # UTC timestamp for JWT
        })
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.JWT_SECRET_KEY, 
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    

    @staticmethod
    def _generate_tokens(
        db: Session,
        user: User,
        client: Client
    ) -> Tuple[AccessToken, RefreshToken]:
        try:

            current_utc = datetime.now(pytz.UTC)
            access_token_expires = current_utc + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            refresh_token_expires = current_utc + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

            # Create access token payload
            access_token_data = {
                "email": user.email,
                "role": user.role.name,
                "type": "access",
                "client_id": client.client_id,
            }
            
            # Generate JWT access token
            access_token_jwt = UserService.create_jwt_token(
                access_token_data, 
                timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )

            # Create refresh token payload
            refresh_token_data = {
                "sub": str(user.id),
                "type": "refresh",
                "client_id": client.client_id
            }
            
            # Generate JWT refresh token
            refresh_token_jwt = UserService.create_jwt_token(
                refresh_token_data,
                timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            )

            # Create access token record
            access_token = AccessToken(
                token=access_token_jwt,
                user_id=user.id,
                client_id=client.id,
                scopes=client.scope,
                expires_at=access_token_expires
            )
            db.add(access_token)
            db.flush()

            # Create refresh token record
            refresh_token = RefreshToken(
                token=refresh_token_jwt,
                access_token_id=access_token.id,
                expires_at=refresh_token_expires
            )
            db.add(refresh_token)
            db.flush()

            return access_token, refresh_token

        except Exception as e:
            db.rollback()
            logger.error(f"Error generating tokens: {str(e)}")
            raise

    @staticmethod
    def verify_jwt_token(token: str) -> dict:
        """
        Verify a JWT token and return its payload
        """
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            return None
    

    @staticmethod
    async def resend_verification_email(db: Session, email: str):
        """
        Resend verification email if user exists and isn't verified
        """
        logger.info(f"Resend verification email request for: {email}")
        
        try:
            # Find user
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                logger.warning(f"Resend verification failed - user not found: {email}")
                raise UserNotFoundError()
                
            if user.is_verified:
                logger.warning(f"Resend verification failed - user already verified: {email}")
                raise UserAlreadyVerifiedError()
            
            if not user.verification_code:
                logger.warning(f"Resend verification failed - no pending verification: {email}")
                raise NoVerificationPendingError()

            # Generate new verification code
            verification_code = generate_verification_code()
            
            # Update user with new code and expiration
            current_time = datetime.now(pytz.UTC)
            user.verification_code = verification_code
            user.verification_code_expires_at = current_time + timedelta(minutes=10)
            
            try:
                # Try to send email
                await send_verification_email(user.email, verification_code)
                
                # If email sends successfully, commit the transaction
                db.commit()
                logger.info(f"Verification email resent successfully to: {email}")
                return user
                
            except Exception as email_error:
                db.rollback()
                logger.error(f"Failed to resend verification email: {str(email_error)}")
                raise Exception("Failed to send verification email") from email_error
                
        except (UserNotFoundError, UserAlreadyVerifiedError, 
                NoVerificationPendingError) as e:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Resend verification failed: {str(e)}")
            raise



    @staticmethod
    async def initiate_email_login(db: Session, email: str):
        """
        Initiate email-based login by sending verification code
        """
        logger.info(f"Email login initiation for: {email}")
        
        try:
            # Check if user exists
            user = db.query(User).filter(User.email == email).first()
            
            if user:
                if not user.is_active:
                    logger.warning(f"Inactive user attempted email login: {email}")
                    raise UserNotActiveError()
                
                message = "Login verification code sent to your email."
            else:
                # Create new user with minimal info
                firstname = email.split('@')[0]  # Use email prefix as firstname
                role = db.query(Role).filter(Role.name == "USER").first()
                
                if not role:
                    role = Role(
                        name="USER",
                        description="Default user role with basic privileges"
                    )
                    db.add(role)
                    db.flush()
                
                user = User(
                    email=email,
                    firstname=firstname,
                    lastname="",  # Empty lastname for email-based registration
                    role_id=role.id,
                    is_active=True,  
                    is_verified=False 
                )
                db.add(user)
                db.flush()
                message = "Account created. Please check your email to verify."
                
            # Generate and save verification code
            verification_code = generate_verification_code()
            current_time = datetime.now(pytz.UTC)
            
            user.verification_code = verification_code
            user.verification_code_expires_at = current_time + timedelta(minutes=10)
            
            # Send verification email
            try:
                await send_verification_email(user.email, verification_code)
                db.commit()
                logger.info(f"Email login verification code sent to: {email}")
                
                return StandardResponse(
                    status=True,
                    message=message
                )
                
            except Exception as email_error:
                db.rollback()
                logger.error(f"Failed to send verification email: {str(email_error)}")
                raise Exception("Failed to send verification email") from email_error
                
        except (UserNotActiveError, Exception) as e:
            if not isinstance(e, UserNotActiveError):
                db.rollback()
            logger.error(f"Email login initiation failed: {str(e)}")
            raise

    @staticmethod
    async def verify_email_login(
        db: Session,
        email: str,
        verification_code: str,
        user_agent_string: str
    ) -> dict:
        """
        Verify email login with verification code and generate tokens
        """
        logger.info(f"Email login verification attempt for: {email}")
        
        try:
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                logger.warning(f"Verification failed - user not found: {email}")
                raise InvalidVerificationCodeError()
                
            if not user.verification_code or user.verification_code != verification_code:
                logger.warning(f"Verification failed - invalid code for user: {email}")
                raise InvalidVerificationCodeError()
            
            current_time = datetime.now(pytz.UTC)
            if user.verification_code_expires_at < current_time:
                logger.warning(f"Verification failed - code expired for user: {email}")
                raise VerificationCodeExpiredError()
            
            # Get appropriate client based on user agent
            client = UserService._get_client_by_user_agent(db, user_agent_string)
            
            # Generate tokens
            access_token, refresh_token = UserService._generate_tokens(db, user, client)
            
            # Update user status
            user.is_active=True
            user.is_verified = True
            user.verification_code = None
            user.verification_code_expires_at = None
            
            # Prepare response data
            auth_data = {
                "access_token": access_token.token,
                "access_token_expires_time": access_token.expires_at.isoformat(),
                "refresh_token": refresh_token.token,
                "refresh_token_expires_time": refresh_token.expires_at.isoformat()
            }
            
            user_info = {
                "firstname": user.firstname,
                "lastname": user.lastname,
                "email": user.email,
                "role": user.role.name
            }
            
            # encrypted_data = UserService.encrypt_data(auth_data)
            
            response_data = {
                "auth": auth_data,
                "userinfo": user_info
            }
            encrypted_data = UserService.encrypt_data(auth_data)
            
            # Commit all changes
            db.commit()
            logger.info(f"Email login successful for user: {email}")
            
            return {
                "status": True,
                "message": "Login successful",
                "data": encrypted_data
            }
            
        except (InvalidVerificationCodeError, VerificationCodeExpiredError, 
                ClientNotFoundError) as e:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Email login verification failed: {str(e)}")
            raise

    # Add these class variables at the top of UserService
    
    @classmethod
    async def verify_google_token(cls, token: str) -> Dict:
        """
        Verify Google OAuth token and get user information
        """
        logger.info("Verifying Google OAuth token")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{cls.GOOGLE_TOKEN_VERIFY_URL}?id_token={token}"
                ) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        logger.error(f"Google token verification failed: {error_data}")
                        raise InvalidCredentialsError("Invalid Google token")
                        
                    user_data = await response.json()
                    logger.info("Google token verified successfully")
                    
                    return {
                        "email": user_data["email"],
                        "given_name": user_data.get("given_name", ""),
                        "family_name": user_data.get("family_name", ""),
                        # "picture": user_data.get("picture")
                    }
                    
            except aiohttp.ClientError as e:
                logger.error(f"Failed to verify Google token: {str(e)}")
                raise InvalidCredentialsError("Failed to verify Google token")

    @classmethod
    async def handle_google_auth(
        cls,
        db: Session,
        token: str,
        user_agent_string: str
    ) -> Dict:
        """
        Handle Google OAuth authentication - both registration and login
        """
        logger.info("Processing Google authentication request")
        
        try:
            # Verify Google token and get user info
            google_user_info = await cls.verify_google_token(token)
            email = google_user_info["email"]
            
            # Check if user exists
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                logger.info(f"New Google user registration: {email}")
                # Register new user
                role = db.query(Role).filter(Role.name == "USER").first()
                if not role:
                    role = Role(
                        name="USER",
                        description="Default user role with basic privileges"
                    )
                    db.add(role)
                    db.flush()
                
                user = User(
                    email=email,
                    firstname=google_user_info["given_name"],
                    lastname=google_user_info["family_name"],
                    role_id=role.id,
                    is_active=True,
                    is_verified=True  # Google users are pre-verified
                )
                db.add(user)
                db.flush()
                logger.info(f"Created new user account for Google user: {email}")
            else:
                logger.info(f"Existing Google user login: {email}")
                if not user.is_active:
                    logger.warning(f"Inactive Google user attempted login: {email}")
                    raise UserNotActiveError()

            # Get appropriate client based on user agent
            client = cls._get_client_by_user_agent(db, user_agent_string)
            
            # Generate tokens
            access_token, refresh_token = cls._generate_tokens(db, user, client)
            
            # Prepare response data
            auth_data = {
                "access_token": access_token.token,
                "access_token_expires_time": access_token.expires_at.isoformat(),
                "refresh_token": refresh_token.token,
                "refresh_token_expires_time": refresh_token.expires_at.isoformat()
            }
            
            user_info = {
                "firstname": user.firstname,
                "lastname": user.lastname,
                "email": user.email,
                "role": user.role.name
            }
            
            # Encrypt authentication data
            # encrypted_data = cls.encrypt_data(auth_data)
            
            
            response_data = {
                "auth": auth_data,
                "userinfo": user_info
            }

            encrypted_data = cls.encrypt_data(auth_data)


            # Commit all changes
            db.commit()
            logger.info(f"Google authentication successful for user: {email}")
            
            return {
                "status": True,
                "message": "Google authentication successful",
                "data": encrypted_data
            }
            
        except (InvalidCredentialsError, UserNotActiveError, 
                ClientNotFoundError) as e:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Google authentication failed: {str(e)}")
            raise