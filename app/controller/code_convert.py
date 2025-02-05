# controllers/code_convert.py
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.code_convert import CodeConvertRequest, StandardResponse
from app.services.code_convert import CodeConvertService
from app.exceptions.custom_exceptions import CustomException
from app.helpers.auth import optional_auth, strict_auth
from app.helpers.auth import get_system_ip
from app.models.user import Guest
from logzero import logger

router = APIRouter()



# still inprocess - need to complete
@router.post("/convert-code", response_model=StandardResponse)
async def convert_code(
    request: Request,
    convert_data: CodeConvertRequest,
    db: Session = Depends(get_db),
    auth_info: dict = Depends(optional_auth)
):
    try:
        if not auth_info["authenticated"]:
            # Guest user logic
            guest_data = auth_info["guest_data"]
            if guest_data["credits_remaining"] <= 0:
                raise CustomException(
                    message="Free trial expired. Please login to continue using the service."
                )
            
            # Decrease credit balance
            guest = db.query(Guest).filter(
                Guest.ip_address == guest_data["ip_address"]
            ).first()
            guest.credit_balance -= 1
            db.commit()
        
        result = await CodeConvertService.convert_code(
            convert_data.source_code,
            convert_data.source_language,
            convert_data.target_language
        )
        
        return StandardResponse(
            status=True,
            message="Code converted successfully",
            data={
                "converted_code": result,
                "credits_remaining": None if auth_info["authenticated"] else guest_data["credits_remaining"] - 1
            }
        )
    except CustomException as ce:
        return StandardResponse(status=False, message=ce.message, data=ce.data)
    except Exception as e:
        logger.error(f"Unexpected error during code conversion: {str(e)}")
        raise HTTPException(status_code=500, detail="Code conversion failed")

@router.post("/protected route", response_model=StandardResponse)
async def advanced_convert(
    request: Request,
    convert_data: CodeConvertRequest,
    user_data: dict = Depends(strict_auth)
):
    try:
        result = await CodeConvertService.advanced_convert(
            convert_data.source_code,
            convert_data.source_language,
            convert_data.target_language,
            user_data
        )
        
        return StandardResponse(
            status=True,
            message="Advanced code conversion completed",
            data={"converted_code": result}
        )
    except CustomException as ce:
        return StandardResponse(status=False, message=ce.message, data=ce.data)
    except Exception as e:
        logger.error(f"Unexpected error during advanced code conversion: {str(e)}")
        raise HTTPException(status_code=500, detail="Advanced code conversion failed")
    

@router.get("/check-ip", response_model=StandardResponse)
async def check_ip():
    """Test endpoint to check system IP"""
    try:
        ip = get_system_ip()
        return StandardResponse(
            status=True,
            message="System IP retrieved",
            data={"system_ip": ip}
        )
    except Exception as e:
        logger.error(f"Error checking IP: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve IP information"
        )