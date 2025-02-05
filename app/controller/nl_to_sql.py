# routes/nl_to_sql.py
from fastapi import APIRouter, HTTPException
from logzero import logger
from app.schemas.nl_to_sql import NLToSQLRequest, NLToSQLResponse
from app.services.nl_to_sql import NLToSQLService
from app.exceptions.nl_to_sql_exceptions import NLToSQLError

router = APIRouter()
nl_to_sql_service = NLToSQLService()

@router.post("/convert", response_model=NLToSQLResponse)
async def convert_nl_to_sql(request: NLToSQLRequest):
    """
    Convert natural language question to SQL query
    """
    try:
        result = await nl_to_sql_service.convert_to_sql(request)
        return NLToSQLResponse(**result)
        
    except NLToSQLError as e:
        logger.error(f"NL to SQL error: {str(e)}")
        raise HTTPException(
            status_code=e.status_code,
            detail={"message": e.message}
        )
    except Exception as e:
        logger.error(f"Unexpected error in NL to SQL conversion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error during conversion"}
        )