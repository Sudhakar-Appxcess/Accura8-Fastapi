# controllers/user.py
from fastapi import APIRouter, Depends, Header, Request,HTTPException
from sqlalchemy.orm import Session
from logzero import logger
from app.db import get_db
from app.schemas.user import UserRegisterRequest, StandardResponse, EmailVerificationRequest
from app.services.user import UserService
from app.exceptions.custom_exceptions import CustomException
from app.schemas.user import LoginRequest,ResendVerificationRequest,EmailLoginVerificationRequest,EmailOnlyLoginRequest,GoogleAuthRequest
from typing import Optional
from app.helpers.recaptcha import verify_recaptcha
from fastapi.responses import JSONResponse


router = APIRouter()

@router.post("/register", response_model=StandardResponse)
async def register(
    user_data: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    try:
        # Verify reCAPTCHA first
        # if not await verify_recaptcha(user_data.recaptcha):
        #     raise CustomException(message="reCAPTCHA verification failed")

        result = await UserService.register_user(db, user_data)
        # Check if this was a new registration or verification resend
        if result.get("is_new_registration", True):
            return JSONResponse(
                status_code=201,  # Created
                content=StandardResponse(
                    status=True,
                    message="Registration successful! Please check your email to verify your account."
                ).dict()
            )
        else:
            return JSONResponse(
                status_code=200,  # OK
                content=StandardResponse(
                    status=True,
                    message="User already registered, Verification code has been resent. Please check your email."
                ).dict()
            )
    except CustomException as ce:
        raise HTTPException(
            status_code=ce.status_code,
            detail=StandardResponse(
                status=False,
                message=ce.message,
                data=ce.data
            ).dict()
        )
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=StandardResponse(
                status=False,
                message="Registration failed due to server error"
            ).dict()
        )

@router.post("/verify-email", response_model=StandardResponse)
async def verify_email(
    verification_data: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    try:
        await UserService.verify_email(
            db, 
            verification_data.email, 
            verification_data.verification_code
        )
        return StandardResponse(
            status=True,
            message="Email verified successfully!"
        )

    except CustomException as ce:  
        raise HTTPException(
            status_code=ce.status_code,
            detail=StandardResponse(
                status=False,
                message=ce.message,
                data=ce.data
            ).dict()
        )
    
    except Exception as e:
        logger.error(f"Unexpected error during email verification: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Email verification failed due to server error"
        )


@router.post("/login", response_model=StandardResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    user_agent: Optional[str] = Header(None)
):
    try:
        if not await verify_recaptcha(login_data.recaptcha):
            raise CustomException(message="reCAPTCHA verification failed")
        
        logger.info("reCAPTCHA verification success")
        
        result = await UserService.login(
            db,
            login_data.email,
            login_data.password,
            user_agent or request.headers.get("user-agent", "")
        )

        
        return StandardResponse(**result)
                
    except CustomException as ce:
        raise HTTPException(
            status_code=ce.status_code,
            detail=StandardResponse(
                status=False,
                message=ce.message,
                data=ce.data
            ).dict()
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Login failed due to server error"
        )

@router.post("/resend-verification", response_model=StandardResponse)
async def resend_verification(
    verification_data: ResendVerificationRequest,
    db: Session = Depends(get_db)
):
    try:
        await UserService.resend_verification_email(
            db, 
            verification_data.email
        )
        return StandardResponse(
            status=True,
            message="Verification email has been resent. Please check your inbox."
        )
        
    except CustomException as ce:
        raise HTTPException(
            status_code=ce.status_code,
            detail=StandardResponse(
                status=False,
                message=ce.message,
                data=ce.data
            ).dict()
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during resend verification: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to resend verification email due to server error"
        )
    


@router.post("/email-login", response_model=StandardResponse)
async def initiate_email_login(
    login_data: EmailOnlyLoginRequest,
    db: Session = Depends(get_db)
):
    try:
         # Verify reCAPTCHA first
        # if not await verify_recaptcha(login_data.recaptcha):
        #     raise CustomException(message="reCAPTCHA verification failed")
        
        result = await UserService.initiate_email_login(
            db,
            login_data.email
        )
        return result
        
    except CustomException as ce:
        raise HTTPException(
            status_code=ce.status_code,
            detail=StandardResponse(
                status=False,
                message=ce.message,
                data=ce.data
            ).dict()
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during email login initiation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to initiate email login due to server error"
        )

@router.post("/email-login/verify", response_model=StandardResponse)
async def verify_email_login(
    request: Request,
    verification_data: EmailLoginVerificationRequest,
    db: Session = Depends(get_db),
    user_agent: Optional[str] = Header(None)
):
    try:
        result = await UserService.verify_email_login(
            db,
            verification_data.email,
            verification_data.verification_code,
            user_agent or request.headers.get("user-agent", "")
        )

     
        return StandardResponse(**result)
        
    except CustomException as ce:
        raise HTTPException(
            status_code=ce.status_code,
            detail=StandardResponse(
                status=False,
                message=ce.message,
                data=ce.data
            ).dict()
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during email login verification: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to verify email login due to server error"
        )
    

@router.post("/google-auth", response_model=StandardResponse)
async def google_auth(
    request: Request,
    auth_data: GoogleAuthRequest,
    db: Session = Depends(get_db),
    user_agent: Optional[str] = Header(None)
):
    """
    Handle Google OAuth2.0 authentication
    """
    try:
        result = await UserService.handle_google_auth(
            db,
            auth_data.token,
            user_agent or request.headers.get("user-agent", "")
        )

       
        return StandardResponse(**result)
        
    except CustomException as ce:
        raise HTTPException(
            status_code=ce.status_code,
            detail=StandardResponse(
                status=False,
                message=ce.message,
                data=ce.data
            ).dict()
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during Google authentication: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Google authentication failed due to server error"
        )