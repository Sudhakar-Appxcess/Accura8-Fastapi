# routes/sql_migration.py
from fastapi import APIRouter, HTTPException
from logzero import logger
from app.schemas.sql_migration import SQLMigrationRequest, SQLMigrationResponse
from app.services.sql_migration import SQLMigrationService
from app.exceptions.sql_migration_exceptions import SQLMigrationError

router = APIRouter()
sql_migration_service = SQLMigrationService()

@router.post("/migrate", response_model=SQLMigrationResponse)
async def migrate_sql(request: SQLMigrationRequest):
    """
    Migrate SQL query from source database to target database
    """
    try:
        result = await sql_migration_service.migrate_sql(request)
        return SQLMigrationResponse(**result)
        
    except SQLMigrationError as e:
        logger.error(f"SQL migration error: {str(e)}")
        raise HTTPException(
            status_code=e.status_code,
            detail={"message": e.message}
        )
    except Exception as e:
        logger.error(f"Unexpected error in SQL migration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error during SQL migration"}
        )