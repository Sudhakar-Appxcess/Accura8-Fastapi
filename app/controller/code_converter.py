# controllers/code_converter.py
from fastapi import APIRouter, HTTPException
from logzero import logger
from app.schemas.code_converter import (
    CodeConversionRequest,
    CodeConversionResponse,
    ProgrammingLanguage
)
from app.services.code_converter import CodeConverterService
from app.exceptions.code_converter_exceptions import (
    APIKeyNotFoundError,
    ModelNotAvailableError,
    InvalidRequestError,
    ConversionError
)
from app.services.code_validator import CodeValidatorService

router = APIRouter()
code_converter_service = CodeConverterService()

@router.get("/languages")
async def get_supported_languages():
    """Get list of supported programming languages"""
    try:
        languages = [lang.value for lang in ProgrammingLanguage]
        return {
            "status": True,
            "message": "Supported languages retrieved successfully",
            "data": {"supported_languages": languages}
        }
    except Exception as e:
        logger.error(f"Error retrieving supported languages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve supported languages")

@router.post("/convert", response_model=CodeConversionResponse)
async def convert_code(request: CodeConversionRequest):
    """Convert code from one programming language to another"""
    try:
        logger.info(f"Received code conversion request: {request.source_language} -> {request.target_language}")
        
        # Perform the code conversion
        result = await code_converter_service.convert_code(request)
        
        return CodeConversionResponse(
            status=True,
            message="Code converted successfully",
            data=result
        )
        
    except APIKeyNotFoundError as e:
        logger.error(f"API key error: {str(e)}")
        raise HTTPException(status_code=500, detail="API configuration error")
        
    except ModelNotAvailableError as e:
        logger.error(f"Model error: {str(e)}")
        raise HTTPException(status_code=503, detail="Code conversion service unavailable")
        
    except InvalidRequestError as e:
        logger.error(f"Invalid request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except ConversionError as e:
        logger.error(f"Conversion error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
        
    except Exception as e:
        logger.error(f"Unexpected error during code conversion: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/validate")
async def validate_code(request: CodeConversionRequest):
    """
    Validate code before conversion
    
    Performs comprehensive validation including:
    - Syntax checking
    - Code complexity analysis
    - Comment detection and analysis
    - Potential issues identification
    """
    try:
        logger.info(f"Received validation request for {request.source_language} code")
        
        # Perform comprehensive validation
        validation_result = CodeValidatorService.validate_code(request)
        
        return {
            "status": validation_result["is_valid"],
            "message": validation_result["syntax_message"],
            "data": validation_result
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during validation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during code validation"
        )