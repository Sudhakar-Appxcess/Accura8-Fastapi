import mysql.connector
from mysql.connector import Error as MySQLError
from typing import Dict, List, Any, Optional, Tuple, Union
from logzero import logger
import re
import sqlparse
from sqlalchemy.sql import text
from sqlalchemy.engine.url import URL
from sqlalchemy import create_engine, inspect

# Optional imports with proper error handling
try:
    import psycopg2
    from psycopg2.extensions import quote_ident
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    
try:
    import oracledb
    ORACLE_AVAILABLE = True
except ImportError:
    ORACLE_AVAILABLE = False

class SQLInjectionError(Exception):
    """Custom exception for SQL injection attempts"""
    pass

class DatabaseConnector:
    """Base class for database connectors with security measures"""
    
    # List of dangerous SQL keywords and patterns
    DANGEROUS_PATTERNS = [
        r'--',                    # SQL comments
        r'/\*.*?\*/',            # Multi-line comments
        r';.*?$',                # Multiple statements
        r'UNION\s+ALL\s+SELECT', # UNION-based injection
        r'OR\s+1\s*=\s*1',       # OR-based injection
        r'DROP\s+TABLE',         # Table dropping
        r'DELETE\s+FROM',        # Mass deletion
        r'UPDATE\s+.*SET',       # Mass update
        r'EXECUTE\s+IMMEDIATE',  # Dynamic SQL execution
        r'EXEC\s+xp_',           # Extended stored procedures
        r'xp_cmdshell'           # Command shell execution
    ]
    
    # Allowed SQL operations for queries
    ALLOWED_OPERATIONS = {
        'SELECT', 'WITH', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 
        'ORDER BY', 'LIMIT', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 
        'INNER JOIN', 'OUTER JOIN', 'ON', 'AND', 'OR', 'IN', 
        'BETWEEN', 'LIKE', 'AS'
    }
    
    def __init__(self, config: Dict[str, Any]):
        self.config = self._sanitize_config(config)
        self.connection = None
        self.cursor = None

    def _sanitize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize configuration parameters"""
        sanitized = {}
        for key, value in config.items():
            if isinstance(value, str):
                # Remove any dangerous characters from config values
                sanitized[key] = re.sub(r'[;\'\"\\]', '', value)
            else:
                sanitized[key] = value
        return sanitized

    def _validate_query(self, query: str) -> None:
        """
        Validate SQL query for potential security threats
        Raises SQLInjectionError if suspicious patterns are found
        """
        # Parse the SQL query
        parsed = sqlparse.parse(query)[0]
        
        # Check for dangerous patterns
        query_upper = query.upper()
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE):
                raise SQLInjectionError(f"Potential SQL injection detected: {pattern}")

        # Validate SQL operations
        tokens = [token.value.upper() for token in parsed.tokens if token.is_keyword]
        for token in tokens:
            if token not in self.ALLOWED_OPERATIONS:
                raise SQLInjectionError(f"Unauthorized SQL operation detected: {token}")

        # Check for stacked queries
        if query.count(';') > 1:
            raise SQLInjectionError("Multiple SQL statements are not allowed")

        # Check for comment markers
        if '--' in query or '/*' in query:
            raise SQLInjectionError("SQL comments are not allowed")

    def _sanitize_identifier(self, identifier: str) -> str:
        """Sanitize SQL identifiers (table names, column names)"""
        # Remove any dangerous characters
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', identifier)
        if not sanitized:
            raise ValueError("Invalid SQL identifier")
        return sanitized

    def connect(self):
        """Establish database connection"""
        raise NotImplementedError

    def disconnect(self):
        """Close database connection safely"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
        finally:
            self.cursor = None
            self.connection = None

    def execute_query(self, query: str, params: Optional[Union[tuple, dict]] = None) -> tuple:
        """
        Execute a query with security validations and parameter binding
        
        Args:
            query: SQL query string
            params: Query parameters for binding
            
        Returns:
            Query results
            
        Raises:
            SQLInjectionError: If potential SQL injection is detected
        """
        if not self.connection:
            self.connect()

        try:
            # Validate the query before execution
            self._validate_query(query)
            
            # Execute with parameter binding
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
                
            return self.cursor.fetchall()
            
        except SQLInjectionError:
            raise
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            raise

    def get_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Extract database schema safely"""
        raise NotImplementedError

# class MySQLConnector(DatabaseConnector):
#     """MySQL database connector with security measures"""
    
#     def connect(self):
#         try:
#             # Use pure Python implementation for better security
#             self.connection = mysql.connector.connect(
#                 **self.config,
#                 use_pure=True,
#                 ssl_verify_cert=True,  # Verify SSL certificate
#                 ssl_verify_identity=True,  # Verify server identity
#                 allow_local_infile=False,  # Disable local file access
#                 sql_mode='NO_ENGINE_SUBSTITUTION,STRICT_TRANS_TABLES'  # Strict SQL mode
#             )
#             self.cursor = self.connection.cursor(prepared=True)  # Use prepared statements
#         except mysql.connector.Error as e:
#             logger.error(f"MySQL connection error: {str(e)}")
#             raise
class MySQLConnector(DatabaseConnector):
    """MySQL database connector with security measures"""
    
    def connect(self):
        try:
            # Remove use_pure from config if it exists to prevent duplicate
            connect_params = self.config.copy()
            connect_params.pop('use_pure', None)
            
            # Add security parameters
            security_params = {
                'use_pure': True,
                'ssl_verify_cert': False,
                'ssl_verify_identity': False,
                'allow_local_infile': False,
                'sql_mode': 'NO_ENGINE_SUBSTITUTION,STRICT_TRANS_TABLES'
            }
            
            # Create final connection parameters
            final_params = {**connect_params, **security_params}
            
            # Establish connection
            self.connection = mysql.connector.connect(**final_params)
            self.cursor = self.connection.cursor(prepared=True)  # Use prepared statements
            
        except mysql.connector.Error as e:
            logger.error(f"MySQL connection error: {str(e)}")
            raise

    def get_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        if not self.connection:
            self.connect()
            
        schema = {}
        try:
            # Get all tables using safe queries
            self.cursor.execute("SHOW TABLES")
            tables = self.cursor.fetchall()
            
            for (table_name,) in tables:
                # Sanitize table name
                safe_table_name = self._sanitize_identifier(table_name)
                
                # Use prepared statement for column information
                self.cursor.execute(
                    "SHOW COLUMNS FROM `%s`" % safe_table_name
                )
                columns = self.cursor.fetchall()
                
                schema[table_name] = [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "YES",
                        "key": col[3],
                        "default": col[4],
                        "extra": col[5]
                    }
                    for col in columns
                ]
                
            return schema
        except mysql.connector.Error as e:
            logger.error(f"MySQL schema extraction error: {str(e)}")
            raise

class PostgreSQLConnector(DatabaseConnector):
    """PostgreSQL database connector with security measures"""
    
    def __init__(self, config: Dict[str, Any]):
        if not POSTGRES_AVAILABLE:
            raise ImportError(
                "PostgreSQL support requires psycopg2. "
                "Please install it with: pip install psycopg2-binary"
            )
        super().__init__(config)
    
    def connect(self):
        try:
            # connect_params = {
            #     **self.config,
            #     'application_name': 'SecureDatabaseValidator',
            #     'sslmode': 'verify-full',  # Require SSL with verification
            #     'options': '-c statement_timeout=30000'  # 30-second query timeout
            # }
            connect_params = {
                **self.config,
                'application_name': 'DatabaseValidator',
                'sslmode': 'disable',  # Disable SSL for development
                'options': '-c statement_timeout=30000'  # 30-second query timeout
            }
            
            required_params = ['host', 'port', 'user', 'password', 'database']
            missing_params = [param for param in required_params if param not in connect_params]
            if missing_params:
                raise ValueError(f"Missing required PostgreSQL connection parameters: {missing_params}")
            
            self.connection = psycopg2.connect(**connect_params)
            self.connection.set_session(
                readonly=True,  # Read-only connection
                autocommit=True  # Prevent transaction manipulation
            )
            
            self.cursor = self.connection.cursor()
            
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL connection error: {str(e)}")
            raise

    def get_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        if not self.connection:
            self.connect()
            
        schema = {}
        try:
            # Use parameterized queries for schema extraction
            self.cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s
            """, ('public',))
            
            tables = self.cursor.fetchall()
            
            for (table_name,) in tables:
                # Use parameterized query for column information
                self.cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        (SELECT 
                            CASE WHEN COUNT(*) > 0 THEN 'PRI' 
                            ELSE '' END
                        FROM information_schema.key_column_usage kcu
                        JOIN information_schema.table_constraints tc 
                        ON kcu.constraint_name = tc.constraint_name
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                        AND kcu.table_name = %s
                        AND kcu.column_name = c.column_name) as key_type
                    FROM information_schema.columns c
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name, table_name))
                
                columns = self.cursor.fetchall()
                
                schema[table_name] = [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "YES",
                        "key": col[4],
                        "default": col[3],
                        "extra": ""
                    }
                    for col in columns
                ]
                
            return schema
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL schema extraction error: {str(e)}")
            raise

class OracleConnector(DatabaseConnector):
    """Oracle database connector with security measures"""
    
    def __init__(self, config: Dict[str, Any]):
        if not ORACLE_AVAILABLE:
            raise ImportError(
                "Oracle support requires oracledb. "
                "Please install it with: pip install oracledb"
            )
        super().__init__(config)
    
    def connect(self):
        try:
            # Configure secure connection
            oracledb.init_oracle_client()
            
            # Format DSN with proper escaping
            dsn = oracledb.makedsn(
                self.config['host'],
                self.config['port'],
                service_name=self.config.get('service_name', self.config.get('database'))
            )
            
            self.connection = oracledb.connect(
                user=self.config['username'],
                password=self.config['password'],
                dsn=dsn,
                encoding='UTF-8',
                nencoding='UTF-8',
                events=True,  # Enable connection events
                ssl_server_dn_match=True,  # Verify server certificate
                ssl_server_cert_dn=self.config.get('ssl_server_cert_dn')  # Server certificate DN
            )
            
            self.cursor = self.connection.cursor()
            
            # Set session parameters for security
            self.cursor.execute("ALTER SESSION SET CURSOR_SHARING = FORCE")
            self.cursor.execute("ALTER SESSION SET SQL_TRACE = FALSE")
            
        except oracledb.Error as e:
            logger.error(f"Oracle connection error: {str(e)}")
            raise

    def get_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        if not self.connection:
            self.connect()
            
        schema = {}
        try:
            # Use bind variables for secure schema extraction
            self.cursor.execute("""
                SELECT table_name 
                FROM user_tables 
                ORDER BY table_name
            """)
            tables = self.cursor.fetchall()
            
            for (table_name,) in tables:
                # Use bind variables in query
                self.cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        nullable,
                        data_default,
                        (SELECT 'PRI' 
                         FROM user_constraints uc
                         JOIN user_cons_columns ucc ON uc.constraint_name = ucc.constraint_name
                         WHERE uc.constraint_type = 'P'
                         AND uc.table_name = :1
                         AND ucc.column_name = c.column_name
                         AND ROWNUM = 1) as key_type
                    FROM user_tab_columns c
                    WHERE table_name = :2
                    ORDER BY column_id
                """, (table_name, table_name))
                
                columns = self.cursor.fetchall()
                
                schema[table_name] = [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "Y",
                        "key": col[4] or "",
                        "default": col[3],
                        "extra": ""
                    }
                    for col in columns
                ]
                
            return schema
        except oracledb.Error as e:
            logger.error(f"Oracle schema extraction error: {str(e)}")
            raise

# def normalize_config(db_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
#     """Normalize and sanitize configuration parameters"""
#     normalized = config.copy()
    
#     # Remove any dangerous characters from string values
#     for key, value in normalized.items():
#         if isinstance(value, str):
#             normalized[key] = re.sub(r'[;\'\"\\]', '', value)
    
#     if db_type.lower() == "postgresql":
#         if 'username' in normalized:
#             normalized['user'] = normalized.pop('username')
#         normalized.setdefault('connect_timeout', 10)
#         normalized.setdefault('client_encoding', 'utf8')
#         normalized.setdefault('sslmode', 'verify-full')
#         normalized.setdefault('application_name', 'SecureDatabaseValidator')
            
#     elif db_type.lower() == "oracle":
#         if 'database' in normalized and 'service_name' not in normalized:
#             normalized['service_name'] = normalized.pop('database')
#         normalized.setdefault('encoding', 'UTF-8')
#         normalized.setdefault('nencoding', 'UTF-8')
#         normalized.setdefault('ssl_server_dn_match', True)
            
#     elif db_type.lower() in ("mysql", "mariadb"):
#         normalized.setdefault('use_pure', True)
#         normalized.setdefault('ssl_verify_cert', True)
#         normalized.setdefault('ssl_verify_identity', True)
#         normalized.setdefault('allow_local_infile', False)
#         normalized.setdefault('sql_mode', 'NO_ENGINE_SUBSTITUTION,STRICT_TRANS_TABLES')
        
#     return normalized
def normalize_config(db_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize configuration parameters"""
    normalized = config.copy()
    
    # Remove any dangerous characters from string values
    for key, value in normalized.items():
        if isinstance(value, str):
            normalized[key] = re.sub(r'[;\'\"\\]', '', value)
    
    # if db_type.lower() == "postgresql":
    #     if 'username' in normalized:
    #         normalized['user'] = normalized.pop('username')
    #     normalized.setdefault('connect_timeout', 10)
    #     normalized.setdefault('client_encoding', 'utf8')
    #     normalized.setdefault('application_name', 'SecureDatabaseValidator')

    if db_type.lower() == "postgresql":
        if 'username' in normalized:
            normalized['user'] = normalized.pop('username')
        normalized.setdefault('connect_timeout', 10)
        normalized.setdefault('client_encoding', 'utf8')
        # Remove SSL-related settings for dev
        normalized.pop('sslmode', None)
        normalized.pop('sslcert', None)
        normalized.pop('sslkey', None)
        normalized.pop('sslrootcert', None)
            
    elif db_type.lower() == "oracle":
        if 'database' in normalized and 'service_name' not in normalized:
            normalized['service_name'] = normalized.pop('database')
        normalized.setdefault('encoding', 'UTF-8')
        normalized.setdefault('nencoding', 'UTF-8')
        normalized.setdefault('ssl_server_dn_match', True)
            
    elif db_type.lower() in ("mysql", "mariadb"):
        # Remove these settings from normalized config as they'll be set in the connector
        # normalized.pop('use_pure', None)
        # normalized.pop('ssl_verify_cert', None)
        # normalized.pop('ssl_verify_identity', None)
        # normalized.pop('allow_local_infile', None)
        # normalized.pop('sql_mode', None)
                # Remove these settings as they'll be handled in the connector
        for param in ['use_pure', 'ssl_verify_cert', 'ssl_verify_identity', 
                     'allow_local_infile', 'sql_mode']:
            normalized.pop(param, None)
        
    return normalized
    
class MariaDBConnector(MySQLConnector):
    """MariaDB connector with inherited MySQL security measures"""
    pass

def get_connector(db_type: str, config: Dict[str, Any]) -> DatabaseConnector:
    """Factory function to get appropriate secure database connector"""
    connectors = {
        "mysql": MySQLConnector,
        "postgresql": PostgreSQLConnector,
        "oracle": OracleConnector,
        "mariadb": MariaDBConnector
    }
    
    connector_class = connectors.get(db_type.lower())
    if not connector_class:
        raise ValueError(f"Unsupported database type: {db_type}")
    
    # Normalize and sanitize configuration
    normalized_config = normalize_config(db_type, config)
    logger.debug(f"Normalized config for {db_type}: {normalized_config}")
        
    return connector_class(normalized_config)

def get_database_connection(db_type: str, config: Dict[str, Any]):
    """Get secure database connection using appropriate connector"""
    connector = get_connector(db_type, config)
    connector.connect()
    return connector.connection

def extract_schema(db_type: str, config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Extract schema securely using appropriate connector"""
    connector = get_connector(db_type, config)
    try:
        return connector.get_schema()
    finally:
        connector.disconnect()

class QueryValidator:
    """Utility class for validating and sanitizing SQL queries"""
    
    @staticmethod
    def validate_and_sanitize_query(query: str, params: Optional[Union[tuple, dict]] = None) -> Tuple[str, Optional[Union[tuple, dict]]]:
        """
        Validate and sanitize SQL query and parameters
        
        Args:
            query: SQL query string
            params: Query parameters for binding
            
        Returns:
            Tuple of (sanitized query, sanitized parameters)
            
        Raises:
            SQLInjectionError: If potential SQL injection is detected
        """
        # Parse the query
        parsed = sqlparse.parse(query)
        if not parsed:
            raise ValueError("Empty or invalid SQL query")
            
        stmt = parsed[0]
        
        # Check query type
        if stmt.get_type() not in ('SELECT', 'UNKNOWN'):
            raise SQLInjectionError("Only SELECT queries are allowed")
            
        # Validate parameters
        if params:
            if isinstance(params, dict):
                sanitized_params = {
                    k: QueryValidator._sanitize_parameter(v)
                    for k, v in params.items()
                }
            else:
                sanitized_params = tuple(
                    QueryValidator._sanitize_parameter(p)
                    for p in params
                )
        else:
            sanitized_params = None
            
        return query, sanitized_params
    
    @staticmethod
    def _sanitize_parameter(value: Any) -> Any:
        """Sanitize individual parameter value"""
        if isinstance(value, str):
            # Remove potential SQL injection patterns
            sanitized = re.sub(r'[;\'"\\]', '', value)
            # Escape special characters
            sanitized = re.sub(r'[%_]', lambda m: '\\' + m.group(0), sanitized)
            return sanitized
        return value