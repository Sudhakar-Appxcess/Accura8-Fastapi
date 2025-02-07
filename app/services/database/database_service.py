
from typing import Optional, List, Any, Dict, Tuple
from datetime import datetime, date
from decimal import Decimal
import time
import json
import re
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine, text
from app.models.databases import Database
from app.schemas.database import DatabaseCreate, TableSchema, DatabaseUpdate
from app.helpers.security.fernet import encrypt_config, decrypt_config
from app.exceptions.database_exceptions import (
    DatabaseErrorFactory,
    DatabaseConnectionError,
    DatabaseAuthenticationError,
    DatabaseConfigError,
    SchemaExtractionError,
    DatabaseQueryError,
    SQLInjectionError
)
from sqlalchemy.sql import func
from app.helpers.db_connectors import (
    get_connector, 
    extract_schema,
    QueryValidator
)

from openai import AsyncOpenAI
from app.config import settings
from logzero import logger
from .response_formatter import DatabaseResponseFormatter

class DatabaseService:
    """Secure database service implementation"""
    
    # Regular expressions for input validation
    NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')
    
    def __init__(self, db: Session):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.response_formatter = DatabaseResponseFormatter(self.client)
        self.query_validator = QueryValidator()

    def _validate_name(self, name: str) -> None:
        """Validate database name for security"""
        if not self.NAME_PATTERN.match(name):
            raise ValueError("Invalid database name. Use only letters, numbers, underscores, and hyphens.")

    def _validate_identifier(self, identifier: str) -> None:
        """Validate SQL identifier for security"""
        if not self.IDENTIFIER_PATTERN.match(identifier):
            raise ValueError("Invalid SQL identifier. Use only letters, numbers, and underscores.")

    def _validate_database_type(self, db_type: str) -> None:
        """Validate database type"""
        allowed_types = {'mysql', 'postgresql', 'oracle', 'mariadb'}
        if db_type.lower() not in allowed_types:
            raise ValueError(f"Unsupported database type. Allowed types: {', '.join(allowed_types)}")

    def create_database(self, user_id: int, db_data: DatabaseCreate) -> tuple[Database, str]:
        """Create a new database connection entry securely"""
        try:
            logger.info(f"Creating database entry for {db_data.name}")
            
            # Validate inputs
            self._validate_name(db_data.name)
            self._validate_database_type(db_data.database_type)
            
            connection_successful = False
            connection_error_message = ""
            
            # Test connection securely
            try:
                self.test_connection(db_data.database_type, db_data.configuration)
                connection_successful = True
            except (DatabaseAuthenticationError, DatabaseConnectionError, DatabaseConfigError) as e:
                connection_error_message = str(e)
                logger.warning(f"Connection test failed: {str(e)}")
            
            # Encrypt sensitive configuration data
            encrypted_config = encrypt_config(db_data.configuration)
            
            db_entry = Database(
                user_id=user_id,
                name=db_data.name,
                database_type=db_data.database_type,
                configuration=encrypted_config,
                is_active=connection_successful
            )
            
            try:
                self.db.add(db_entry)
                self.db.commit()
                self.db.refresh(db_entry)
                
                status_message = (
                    f"Database '{db_data.name}' created successfully"
                    f"{' but connection test failed: ' + connection_error_message if not connection_successful else ''}"
                )
                
                return db_entry, status_message
                
            except IntegrityError:
                self.db.rollback()
                logger.error(f"Database name '{db_data.name}' already exists for user {user_id}")
                raise ValueError(f"Database name '{db_data.name}' already exists")
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database creation error: {str(e)}")
            raise DatabaseConfigError(f"Failed to create database: {str(e)}")

    def test_connection(self, db_type: str, config: dict) -> bool:
        """Test database connection securely"""
        try:
            self._validate_database_type(db_type)
            connector = get_connector(db_type, config)
            
            try:
                connector.connect()
                # Execute a simple test query using parameter binding
                connector.execute_query("SELECT 1", ())
                return True
            finally:
                connector.disconnect()
                
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            error_handler = DatabaseErrorFactory.get_handler(db_type)
            error = error_handler.get_error(str(e))
            
            if error.category.value == "AUTHENTICATION_FAILED":
                raise DatabaseAuthenticationError(error.message)
            elif error.category.value == "CONNECTION_REFUSED":
                raise DatabaseConnectionError(error.message)
            else:
                raise DatabaseConfigError(error.message)

    async def process_query(self, database: Database, sql_query: str) -> Dict[str, Any]:
        """Process query securely with validation"""
        try:
            # Validate and sanitize query
            sanitized_query, params = QueryValidator.validate_and_sanitize_query(sql_query)
            
            # Execute query and get results
            raw_results = self.execute_query(database, sanitized_query, params)
            return await self.response_formatter.format_response(raw_results)
            
        except SQLInjectionError as e:
            logger.error(f"SQL injection attempt detected: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Query processing error: {str(e)}")
            raise

    def execute_query(self, database: Database, sql_query: str, params: Optional[Any] = None) -> Dict[str, Any]:
        """Execute SQL query securely with parameter binding"""
        try:
            if not sql_query.strip():
                raise DatabaseQueryError("Empty or invalid SQL query")
                    
            config = decrypt_config(database.configuration)
            connector = get_connector(database.database_type, config)
            
            try:
                start_time = time.time()
                
                # Execute query with parameter binding
                results = connector.execute_query(sql_query, params)
                execution_time = time.time() - start_time
                
                columns = [desc[0] for desc in connector.cursor.description]
                formatted_results = self._format_query_results(results, columns)
                
                return {
                    "results": formatted_results,
                    "query": sql_query,
                    "execution_time": round(execution_time, 3),
                    "row_count": len(formatted_results)
                }
            finally:
                connector.disconnect()
                    
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            raise DatabaseQueryError(f"Query execution failed: {str(e)}")

    def _format_query_results(self, results: List[tuple], columns: List[str]) -> List[Dict]:
        """Format query results with secure type handling"""
        formatted_results = []
        for row in results:
            formatted_row = {}
            for col, val in zip(columns, row):
                formatted_row[col] = self._format_value(val)
            formatted_results.append(formatted_row)
        return formatted_results

    def _format_value(self, value: Any) -> Any:
        """Format different data types securely"""
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, bytes):
            return value.hex()  # Convert bytes to hex string for safety
        return value

    async def generate_sql_query(self, schema: List[TableSchema], query: str, database_type: str) -> str:
        """Generate SQL query securely using OpenAI"""
        try:
            schema_text = self._format_schema_for_prompt(schema)
            
            messages = [
                {
                    "role": "system", 
                    "content": (
                        f"You are a secure SQL query generator for {database_type.upper()}. "
                        "Generate parameterized queries using placeholders. "
                        "Never include literal values in the query. "
                        "Use proper quoting for identifiers. "
                        "Return only the SQL query without explanation."
                    )
                },
                {
                    "role": "user",
                    "content": f"""
                        Database Schema:
                        {schema_text}
                        
                        Generate a secure, parameterized {database_type.upper()} query for:
                        {query}
                        
                        Rules:
                        1. Use parameterized queries with placeholders
                        2. No literal values in the query
                        3. Proper identifier quoting
                        4. Only use entities from the schema
                        5. Return ONLY the SQL query
                    """
                }
            ]

            response = await self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            generated_query = response.choices[0].message.content.strip()
            
            # Validate and clean the generated query
            sanitized_query, _ = QueryValidator.validate_and_sanitize_query(generated_query)
            return sanitized_query
                
        except Exception as e:
            logger.error(f"Query generation error: {str(e)}")
            raise ValueError(f"Failed to generate SQL query: {str(e)}")

    def get_user_databases(self, user_id: int) -> List[Database]:
        """Get all databases for a user securely"""
        try:
            databases = (
                self.db.query(Database)
                .filter(Database.user_id == user_id)
                .order_by(Database.name)
                .all()
            )
            
            logger.info(f"Retrieved {len(databases)} databases for user {user_id}")
            return databases
            
        except Exception as e:
            logger.error(f"Error retrieving databases: {str(e)}")
            raise

    def update_database(self, user_id: int, update_data: DatabaseUpdate) -> tuple[Database, str]:
        """Update database configuration securely"""
        try:
            # Validate inputs
            if update_data.new_name:
                self._validate_name(update_data.new_name)
            if update_data.database_type:
                self._validate_database_type(update_data.database_type)
            
            # Get existing database
            existing_db = self.db.query(Database).filter(
                Database.user_id == user_id,
                Database.name == update_data.database_name
            ).first()
            
            if not existing_db:
                raise ValueError(f"Database '{update_data.database_name}' not found")

            # Check for name conflicts
            if update_data.new_name and update_data.new_name != update_data.database_name:
                name_exists = self.db.query(Database).filter(
                    Database.user_id == user_id,
                    Database.name == update_data.new_name
                ).first()
                
                if name_exists:
                    raise ValueError(f"Database name '{update_data.new_name}' already exists")

            connection_successful = True
            connection_error_message = ""
            
            # Test connection if configuration is being updated
            if update_data.configuration or update_data.database_type:
                test_config = (
                    update_data.configuration if update_data.configuration 
                    else decrypt_config(existing_db.configuration)
                )
                test_type = update_data.database_type or existing_db.database_type
                
                try:
                    self.test_connection(test_type, test_config)
                except (DatabaseAuthenticationError, DatabaseConnectionError, DatabaseConfigError) as e:
                    connection_successful = False
                    connection_error_message = str(e)
                    logger.warning(f"Connection test failed during update: {str(e)}")

            # Update database entry securely
            if update_data.new_name:
                existing_db.name = update_data.new_name
            if update_data.database_type:
                existing_db.database_type = update_data.database_type
            if update_data.configuration:
                existing_db.configuration = encrypt_config(update_data.configuration)
            
            # Update connection status
            if update_data.configuration or update_data.database_type:
                existing_db.is_active = connection_successful
                if connection_successful:
                    existing_db.last_connected_at = func.now()

            self.db.commit()
            self.db.refresh(existing_db)
            
            # Prepare status message
            if connection_successful:
                status_message = (
                    f"Database '{update_data.database_name}' updated successfully"
                    f"{' and connection test passed' if update_data.configuration or update_data.database_type else ''}"
                )
            else:
                status_message = (
                    f"Database '{update_data.database_name}' updated but connection test failed: "
                    f"{connection_error_message}"
                )

            return existing_db, status_message

        except IntegrityError:
            self.db.rollback()
            logger.error("Database update failed due to integrity constraint")
            raise ValueError("Database update failed due to integrity constraint")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database update error: {str(e)}")
            raise DatabaseConfigError(f"Failed to update database: {str(e)}")

    def delete_database(self, user_id: int, database_name: str) -> str:
        """Delete a database configuration securely"""
        try:
            # Validate input
            self._validate_name(database_name)
            
            # Find the database with proper filtering
            database = self.db.query(Database).filter(
                Database.user_id == user_id,
                Database.name == database_name
            ).first()
            
            if not database:
                logger.error(f"Database '{database_name}' not found for user {user_id}")
                raise ValueError(f"Database '{database_name}' not found")
            
            # Store name for message
            name = database.name
            
            # Delete the database
            self.db.delete(database)
            self.db.commit()
            
            logger.info(f"Successfully deleted database '{name}' for user {user_id}")
            return f"Database '{name}' has been successfully deleted"
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database deletion error: {str(e)}")
            raise

    def get_database_by_name(self, user_id: int, database_name: str) -> Database:
        """Retrieve database configuration by name securely"""
        try:
            # Validate input
            self._validate_name(database_name)
            
            database = self.db.query(Database).filter(
                Database.user_id == user_id,
                Database.name == database_name
            ).first()
            
            if not database:
                logger.error(f"Database '{database_name}' not found")
                raise ValueError(f"Database '{database_name}' not found")
                
            return database
            
        except Exception as e:
            logger.error(f"Error retrieving database: {str(e)}")
            raise

    def extract_database_schema(self, database: Database) -> List[TableSchema]:
        """Extract schema information securely"""
        try:
            config = decrypt_config(database.configuration)
            schema = extract_schema(database.database_type, config)
            
            return [TableSchema(table_name=table, columns=columns) 
                   for table, columns in schema.items()]
                   
        except Exception as e:
            logger.error(f"Schema extraction error: {str(e)}")
            raise SchemaExtractionError(f"Failed to extract schema: {str(e)}")

    def _format_schema_for_prompt(self, schema: List[TableSchema]) -> str:
        """Format schema information securely for OpenAI prompt"""
        formatted = []
        for table in schema:
            # Validate table name
            self._validate_identifier(table.table_name)
            
            columns = self._format_columns(table.columns)
            relationships = self._get_relationships(table.table_name, schema)
            
            formatted.append(
                f"Table: {table.table_name}\n"
                f"Columns: {', '.join(columns)}\n"
                f"Relationships: {relationships}"
            )
        return "\n\n".join(formatted)

    def _format_columns(self, columns: List[Any]) -> List[str]:
        """Format column information securely"""
        formatted_columns = []
        for col in columns:
            # Validate column name
            self._validate_identifier(col.name)
            
            parts = [f"{col.name} ({col.type})"]
            if col.key == 'PRI':
                parts.append("PRIMARY KEY")
            if col.key == 'MUL':
                parts.append("FOREIGN KEY")
            if not col.nullable:
                parts.append("NOT NULL")
            if col.extra == 'auto_increment':
                parts.append("AUTO_INCREMENT")
            formatted_columns.append(" ".join(parts))
        return formatted_columns

    def _get_relationships(self, table_name: str, schema: List[TableSchema]) -> str:
        """Extract and format table relationships securely"""
        relationships = []
        for table in schema:
            # Validate table names
            self._validate_identifier(table.table_name)
            
            for col in table.columns:
                # Validate column names
                self._validate_identifier(col.name)
                
                if col.key == 'MUL' and col.name.lower().endswith('_id'):
                    referenced_table = col.name[:-3]
                    if any(t.table_name.lower() == referenced_table.lower() for t in schema):
                        relationships.append(f"{table.table_name} -> {referenced_table} (via {col.name})")
        return ", ".join(relationships) if relationships else "No direct relationships found"