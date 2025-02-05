# schemas/nl_to_sql.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum

class DatabaseType(str, Enum):
    MYSQL = "mysql"  
    POSTGRESQL = "postgresql"  
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    ORACLE = "oracle"

class NLToSQLRequest(BaseModel):
    question: str
    db_type: DatabaseType
    table_schema: Optional[Dict] = None
    add_explanations: bool = True

class NLToSQLResponse(BaseModel):
    sql_query: str
    explanations: Optional[List[str]] = None
    confidence_score: float