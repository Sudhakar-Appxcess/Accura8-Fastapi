# routes/database.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.database import DatabaseCreate, DatabaseResponse, DatabaseQueryResponse,DatabaseQueryRequest,DatabaseNameResponse,DatabaseNamesList,DatabaseUpdate,DatabaseDelete,DatabaseDetailsRequest,DatabaseDetailsResponse
from app.services.database.database_service import DatabaseService
from app.db import get_db
# from app.core.security import get_current_user
from app.models.user import User
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from logzero import logger
from typing import Union
from app.exceptions.database_exceptions import DatabaseQueryError,DatabaseConfigError,DatabaseAuthenticationError,DatabaseConnectionError,SchemaExtractionError,DatabaseInactiveError
router = APIRouter()


@router.post("/create")
async def create_database(
    database_data: DatabaseCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new database connection for the authenticated user and test the connection.
    Returns both the database object and connection status.
    """
    try:

        
        service = DatabaseService(db)

        # # Check if user has reached database limit
        # db_count = service.get_user_database_count(2)
        # if db_count >= 10:  # Example limit
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Maximum number of database connections reached"
        #     )


        logger.info(f"Database data: {database_data}")
        
        database, status_message = service.create_database(
            user_id=2,  # Replace with current_user.id in production
            db_data=database_data
        )
        
        # Return both the database info and the status message
        return {
            "database": DatabaseResponse.model_validate(database),
            "message": status_message,
            "is_active": database.is_active
        }
        
    except DatabaseAuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except DatabaseConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except DatabaseConfigError as e:
        logger.error(f"Configuration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating database connection"
        )
    



@router.post("/ask", response_model=DatabaseQueryResponse)
async def query_database(
    request: DatabaseQueryRequest,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)
    ) -> Union[JSONResponse, StreamingResponse]:
    """
    Execute a natural language query on a specified database
    """
    try:
        service = DatabaseService(db)
        
        # Get database configuration and check active status
        database = service.get_database_by_name(
            user_id=2,  # Replace with current_user.id
            database_name=request.database_name
        )
        
        # Check if database is inactive before proceeding
        if not database.is_active:
            logger.warning(f"Attempt to query inactive database: {database.name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Database '{database.name}' is currently inactive. Please check the connection settings and reactivate the database."
            )
            
        logger.info(f"Database status: active={database.is_active}")
        
        # Extract database schema
        schema = service.extract_database_schema(database)
        
        # Generate SQL query from natural language
        sql_query = await service.generate_sql_query(
            schema=schema,
            query=request.query,
            database_type=database.database_type
        )
        
        # Process and execute the query
        results = await service.process_query(database, sql_query)
        
        logger.info(
            f"Successfully processed query for database "
            f"{database.id} (user: {2})"
        )
        
        # Handle file download responses
        if isinstance(results, dict) and "file_download" in results and isinstance(results["file_download"], StreamingResponse):
            return results["file_download"]
            
        # Return regular JSON response
        return JSONResponse(content=results)

    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except DatabaseQueryError as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except SchemaExtractionError as e:
        logger.error(f"Schema extraction error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing database query"
        )


@router.post("/test")
async def test_database_connection(
    database_data: DatabaseCreate,
    db: Session = Depends(get_db),
):
    """
    Test database connection without creating a database entry
    """
    try:
        service = DatabaseService(db)
        service.test_connection(
            db_type=database_data.database_type,
            config=database_data.configuration
        )
        return {"status": "success", "message": "Database connection successful"}
        
    except DatabaseAuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except DatabaseConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except DatabaseConfigError as e:
        logger.error(f"Configuration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error testing database connection"
        )
    

@router.get("/names", response_model=DatabaseNamesList)
async def get_user_databases(
    db: Session = Depends(get_db),
):
    """
    Get all databases for the authenticated user with filtered information
    """
    try:
        service = DatabaseService(db)
        databases = service.get_user_databases(user_id=2)  # Replace with current_user.id in production
        
        # Convert to response model
        response_data = [
            DatabaseNameResponse(
                name=db.name,
                database_type=db.database_type,
                is_active=db.is_active,
                last_connected_at=db.last_connected_at
            ) 
            for db in databases
        ]
        
        return DatabaseNamesList(
            databases=response_data,
            total_count=len(response_data)
        )
        
    except Exception as e:
        logger.error(f"Error fetching database names: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching database information"
        )

@router.put("/update")
async def update_database(
    update_data: DatabaseUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing database configuration with connection testing
    """
    try:
        service = DatabaseService(db)
        database, status_message = service.update_database(
            user_id=2,  # Replace with current_user.id in production
            update_data=update_data
        )
        
        return {
            "database": DatabaseResponse.model_validate(database),
            "message": status_message,
            "is_active": database.is_active
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating database configuration"
        )
    

@router.delete("/delete")
async def delete_database(
    delete_data: DatabaseDelete ,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)
):
    """
    Delete a database connection for the authenticated user
    """
    try:
        service = DatabaseService(db)
        
        message = service.delete_database(
            user_id=2,  # Replace with current_user.id
            database_name=delete_data.database_name
        )
        
        return {
            "status": "success",
            "message": message
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting database configuration"
        )
    
@router.post("/details", response_model=DatabaseDetailsResponse)
async def get_database_details(
    request: DatabaseDetailsRequest,
    db: Session = Depends(get_db),
):
    """
    Get detailed database information by name.
    Returns database details including encrypted configuration as a string.
    """
    try:
        service = DatabaseService(db)
        
        # Get database configuration
        database = service.get_database_by_name(
            user_id=2,  # Replace with current_user.id
            database_name=request.database_name
        )
        
        # Create response data
        response_data = {
            "id": database.id,
            "name": database.name,
            "database_type": database.database_type,
            "configuration": database.configuration,  # This is already an encrypted string
            "is_active": database.is_active,
            "last_connected_at": database.last_connected_at,
            "created_at": database.created_at
        }
        
        return DatabaseDetailsResponse(**response_data)
        
    except ValueError as e:
        logger.error(f"Database not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error fetching database details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving database details"
        )