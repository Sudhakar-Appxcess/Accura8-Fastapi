# # schemas/database.py
# from enum import Enum
# from pydantic import BaseModel, Field, validator
# from typing import Dict, Any, Optional,List
# from datetime import datetime

# class DatabaseType(str, Enum):
#     MYSQL = "mysql"
#     POSTGRESQL = "postgresql"
#     ORACLE = "oracle"
#     MARIADB = "mariadb"

# class DatabaseCreate(BaseModel):
#     name: str = Field(..., min_length=1, max_length=255)
#     database_type: DatabaseType
#     configuration: Dict[str, Any]
    
#     @validator('configuration')
#     def validate_config(cls, v):
#         required_fields = {'host', 'port', 'username', 'password', 'database'}
#         missing = required_fields - v.keys()
#         if missing:
#             raise ValueError(f"Missing required configuration fields: {missing}")
            
#         try:
#             port = int(v['port'])
#             if not 1 <= port <= 65535:
#                 raise ValueError("Port number must be between 1 and 65535")
#             v['port'] = port
#         except ValueError as e:
#             raise ValueError(f"Invalid port number: {str(e)}")
            
#         return v

# class DatabaseResponse(BaseModel):
#     id: int
#     name: str
#     database_type: str
#     is_active: bool
#     last_connected_at: Optional[datetime] = None
#     created_at: datetime
    
#     class Config:
#         from_attributes = True  # This replaces the old orm_mode=True



# class DatabaseQueryRequest(BaseModel):
#     database_name: str = Field(..., min_length=1, max_length=255)
#     query: str = Field(..., min_length=1)
    
# class DatabaseQueryResponse(BaseModel):
#     results: List[Dict[str, Any]]
#     query: str
#     execution_time: float
#     row_count: int

# # class TableSchema(BaseModel):
# #     table_name: str
# #     columns: List[Dict[str, str]]  # column_name: data_type

# # schemas/database.py
# class ColumnSchema(BaseModel):
#     name: str
#     type: str
#     nullable: bool = True
#     key: Optional[str] = None
#     default: Optional[Any] = None
#     extra: Optional[str] = None

# class TableSchema(BaseModel):
#     table_name: str
#     columns: List[ColumnSchema]




# schemas/database.py
from enum import Enum
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

class DatabaseType(str, Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    MARIADB = "mariadb"

class DatabaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    database_type: DatabaseType
    configuration: Dict[str, Any]
    
    @validator('configuration')
    def validate_config(cls, v):
        required_fields = {'host', 'port', 'username', 'password', 'database'}
        missing = required_fields - v.keys()
        if missing:
            raise ValueError(f"Missing required configuration fields: {missing}")
            
        try:
            port = int(v['port'])
            if not 1 <= port <= 65535:
                raise ValueError("Port number must be between 1 and 65535")
            v['port'] = port
        except ValueError as e:
            raise ValueError(f"Invalid port number: {str(e)}")
            
        return v

class DatabaseResponse(BaseModel):
    id: int
    name: str
    database_type: str
    is_active: bool
    last_connected_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ColumnSchema(BaseModel):
    name: str
    type: str
    nullable: bool = True
    key: Optional[str] = None
    default: Optional[Any] = None
    extra: Optional[str] = None

class TableSchema(BaseModel):
    table_name: str
    columns: List[ColumnSchema]

    class Config:
        from_attributes = True

class DatabaseQueryRequest(BaseModel):
    database_name: str = Field(..., min_length=1, max_length=255)
    query: str = Field(..., min_length=1)

class DatabaseQueryResponse(BaseModel):
    summary: str
    data: Optional[List[Dict[str, Any]]] = None
    execution_time: float
    row_count: int
    excel_download: Optional[Any] = None

    class Config:
        arbitrary_types_allowed = True


class DatabaseNameResponse(BaseModel):
    name: str
    database_type: str
    is_active: bool
    last_connected_at: datetime | None

    class Config:
        from_attributes = True

class DatabaseNamesList(BaseModel):
    databases: List[DatabaseNameResponse]
    total_count: int

class DatabaseUpdate(BaseModel):
    database_name: str  # Current name of the database to update
    new_name: str | None = None
    database_type: str | None = None
    configuration: Dict | None = None


class DatabaseDelete(BaseModel):
    database_name: str


# schemas/database.py

class DatabaseDetailsRequest(BaseModel):
    database_name: str = Field(..., min_length=1, max_length=255)

class DatabaseDetailsResponse(BaseModel):
    id: int
    name: str
    database_type: str
    configuration: str  # Changed to str to handle encrypted configuration
    is_active: bool
    last_connected_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        
    @validator('configuration')
    def validate_configuration(cls, v):
        """Ensure configuration is a string"""
        if not isinstance(v, str):
            raise ValueError('Configuration must be a string')
        return v