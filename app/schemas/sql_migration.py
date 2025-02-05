# schemas/sql_migration.py
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List

class SourceDatabase(str, Enum):
    TERADATA = "teradata"
    REDSHIFT = "redshift" 
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"
    HIVE = "hive"
    DATABRICKS = "databricks"
    SPARKSQL = "sparksql"
    IMPALA = "impala"
    POSTGRES = "postgres"
    CLICKHOUSE = "clickhouse"

class TargetDatabase(str, Enum):
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    CLICKHOUSE = "clickhouse"

class SQLMigrationRequest(BaseModel):
    source_db: SourceDatabase
    target_db: TargetDatabase
    sql_query: str
    preserve_comments: bool = True
    add_explanations: bool = True

class SQLMigrationResponse(BaseModel):
    converted_query: str
    explanations: Optional[List[str]] = None