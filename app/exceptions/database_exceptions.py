# exceptions/database_exceptions.py
from enum import Enum
from typing import Optional, Dict, Type
from dataclasses import dataclass
import re

class DatabaseErrorCategory(Enum):
    CONNECTION_REFUSED = "CONNECTION_REFUSED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    DATABASE_NOT_FOUND = "DATABASE_NOT_FOUND"
    INVALID_HOST = "INVALID_HOST"
    INVALID_PORT = "INVALID_PORT"
    MAX_CONNECTIONS = "MAX_CONNECTIONS"
    TIMEOUT = "TIMEOUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    UNKNOWN = "UNKNOWN"

@dataclass
class DatabaseError:
    """Structured database error information"""
    category: DatabaseErrorCategory
    message: str
    error_code: str
    details: Optional[str] = None

class BaseDatabaseError(Exception):
    """Base exception class for database errors"""
    def __init__(self, message: str, category: DatabaseErrorCategory = DatabaseErrorCategory.UNKNOWN, 
                 error_code: str = "UNKNOWN", details: Optional[str] = None):
        self.message = message
        self.category = category
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)

class DatabaseConnectionError(BaseDatabaseError):
    """Raised when database connection fails"""
    pass

class DatabaseConfigError(BaseDatabaseError):
    """Raised when database configuration is invalid"""
    pass

class DatabaseAuthenticationError(BaseDatabaseError):
    """Raised when database authentication fails"""
    pass

class DatabaseQueryError(BaseDatabaseError):
    """Raised when database authentication fails"""
    pass

class ErrorHandler:
    """Base class for database-specific error handlers"""
    
    def __init__(self):
        self.error_patterns = {}
        self.error_keywords = {}
        self._init_error_patterns()
        self._init_error_keywords()

    def _init_error_patterns(self):
        """Initialize error patterns for specific database"""
        raise NotImplementedError

    def _init_error_keywords(self):
        """Initialize common error keywords across all databases"""
        self.error_keywords = {
            "could not connect to server": (
                DatabaseErrorCategory.CONNECTION_REFUSED,
                "Unable to connect to the database server. Please verify the host and port."
            ),
            "network unreachable": (
                DatabaseErrorCategory.INVALID_HOST,
                "Network is unreachable. The host address appears to be incorrect."
            ),
            "connection refused": (
                DatabaseErrorCategory.CONNECTION_REFUSED,
                "Connection refused. The port number might be incorrect or the server is not running."
            ),
            "invalid port": (
                DatabaseErrorCategory.INVALID_PORT,
                "The specified port number is invalid or incorrect."
            ),
            "password authentication failed": (
                DatabaseErrorCategory.AUTHENTICATION_FAILED,
                "The provided password is incorrect."
            ),
            "role .* does not exist": (
                DatabaseErrorCategory.AUTHENTICATION_FAILED,
                "The specified username does not exist."
            ),
            "database .* does not exist": (
                DatabaseErrorCategory.DATABASE_NOT_FOUND,
                "The specified database does not exist."
            ),
            "host .* is not allowed": (
                DatabaseErrorCategory.PERMISSION_DENIED,
                "Connection not allowed from this host. Check host-based authentication configuration."
            ),
            "timeout expired": (
                DatabaseErrorCategory.TIMEOUT,
                "Connection timed out. The server might be down or there are network issues."
            ),
            "ssl required": (
                DatabaseErrorCategory.CONNECTION_REFUSED,
                "SSL connection is required. Please enable SSL or check SSL configuration."
            )
        }

    def get_error(self, error_msg: str) -> DatabaseError:
        """Map error message to standardized DatabaseError with enhanced pattern matching"""
        error_msg_lower = str(error_msg).lower()
        
        # Check specific error patterns first
        for pattern, (category, message) in self.error_patterns.items():
            if pattern.lower() in error_msg_lower:
                return DatabaseError(
                    category=category,
                    message=message,
                    error_code=pattern,
                    details=error_msg
                )
        
        # Check common keyword patterns with regex support
        for keyword, (category, message) in self.error_keywords.items():
            if re.search(keyword.lower(), error_msg_lower):
                return DatabaseError(
                    category=category,
                    message=message,
                    error_code=f"KEYWORD_{keyword.upper().replace(' ', '_')}",
                    details=error_msg
                )
        
        # Default error
        return DatabaseError(
            category=DatabaseErrorCategory.UNKNOWN,
            message="Failed to connect to the database. Please verify all connection details.",
            error_code="UNKNOWN",
            details=error_msg
        )

class PostgreSQLErrorHandler(ErrorHandler):
    def _init_error_patterns(self):
        self.error_patterns = {
            "28000": (
                DatabaseErrorCategory.AUTHENTICATION_FAILED,
                "Authentication failed. Please check your username and password."
            ),
            "28P01": (
                DatabaseErrorCategory.AUTHENTICATION_FAILED,
                "Incorrect password for user. Please check your password."
            ),
            "3D000": (
                DatabaseErrorCategory.DATABASE_NOT_FOUND,
                "The specified database does not exist. Please check the database name."
            ),
            "08006": (
                DatabaseErrorCategory.CONNECTION_REFUSED,
                "Connection failed. The port number might be incorrect or PostgreSQL is not running."
            ),
            "57P03": (
                DatabaseErrorCategory.MAX_CONNECTIONS,
                "The database has reached its maximum allowed connections."
            ),
            "08001": (
                DatabaseErrorCategory.INVALID_HOST,
                "Could not connect to host. Please verify the hostname is correct."
            ),
            "42501": (
                DatabaseErrorCategory.PERMISSION_DENIED,
                "User lacks required permissions. Please check user privileges."
            ),
            "53300": (
                DatabaseErrorCategory.MAX_CONNECTIONS,
                "Too many connections. Please try again later."
            ),
            "08004": (
                DatabaseErrorCategory.PERMISSION_DENIED,
                "Server rejected the connection. Check host-based authentication configuration."
            )
        }

class MySQLErrorHandler(ErrorHandler):
    def _init_error_patterns(self):
        self.error_patterns = {
            "2005": (
                DatabaseErrorCategory.INVALID_HOST,
                "Could not connect to MySQL server. The host address appears to be incorrect."
            ),
            "2003": (
                DatabaseErrorCategory.CONNECTION_REFUSED,
                "Connection refused. The port number might be incorrect or MySQL is not running."
            ),
            "1045": (
                DatabaseErrorCategory.AUTHENTICATION_FAILED,
                "Access denied. The username or password is incorrect."
            ),
            "1044": (
                DatabaseErrorCategory.PERMISSION_DENIED,
                "Access denied to database. User lacks required permissions."
            ),
            "1049": (
                DatabaseErrorCategory.DATABASE_NOT_FOUND,
                "The specified database does not exist. Please check the database name."
            ),
            "1042": (
                DatabaseErrorCategory.INVALID_HOST,
                "Unable to connect to MySQL server through TCP/IP. Check hostname and network."
            ),
            "1251": (
                DatabaseErrorCategory.AUTHENTICATION_FAILED,
                "Client authentication method is not supported. Check authentication settings."
            ),
            "1040": (
                DatabaseErrorCategory.MAX_CONNECTIONS,
                "Too many connections. Maximum connection limit reached."
            )
        }

class OracleErrorHandler(ErrorHandler):
    def _init_error_patterns(self):
        self.error_patterns = {
            "ORA-12545": (
                DatabaseErrorCategory.INVALID_HOST,
                "Unable to connect. The host address appears to be incorrect."
            ),
            "ORA-12541": (
                DatabaseErrorCategory.CONNECTION_REFUSED,
                "No listener. The port number might be incorrect or the listener is not running."
            ),
            "ORA-01017": (
                DatabaseErrorCategory.AUTHENTICATION_FAILED,
                "Invalid username or password. Please check your credentials."
            ),
            "ORA-12505": (
                DatabaseErrorCategory.DATABASE_NOT_FOUND,
                "Database (SID) does not exist. Please check the database name/SID."
            ),
            "ORA-01031": (
                DatabaseErrorCategory.PERMISSION_DENIED,
                "Insufficient privileges. User lacks required permissions."
            ),
            "ORA-12170": (
                DatabaseErrorCategory.TIMEOUT,
                "Connect timeout occurred. Check network and database availability."
            ),
            "ORA-12514": (
                DatabaseErrorCategory.DATABASE_NOT_FOUND,
                "Service name not found. Please verify the database service name."
            ),
            "ORA-12504": (
                DatabaseErrorCategory.DATABASE_NOT_FOUND,
                "TNS Listener was not given the SERVICE_NAME. Check database configuration."
            ),
            "ORA-12520": (
                DatabaseErrorCategory.MAX_CONNECTIONS,
                "Maximum number of connections exceeded. Try again later."
            )
        }

class MariaDBErrorHandler(MySQLErrorHandler):
    """MariaDB uses same error codes as MySQL"""
    pass

class DatabaseErrorFactory:
    """Factory for creating database-specific error handlers"""
    
    _handlers: Dict[str, Type[ErrorHandler]] = {
        "mysql": MySQLErrorHandler,
        "postgresql": PostgreSQLErrorHandler,
        "oracle": OracleErrorHandler,
        "mariadb": MariaDBErrorHandler
    }

    @classmethod
    def get_handler(cls, db_type: str) -> ErrorHandler:
        """Get the appropriate error handler for the database type"""
        handler_class = cls._handlers.get(db_type.lower())
        if not handler_class:
            raise ValueError(f"Unsupported database type: {db_type}")
        return handler_class()
    

class DatabaseQueryError(Exception):
    """Raised when there's an error executing a database query"""
    pass

class SchemaExtractionError(Exception):
    """Raised when there's an error extracting database schema"""
    pass


class DatabaseNotFoundError(Exception):
    """Raised when database is not found"""
    pass

class DatabaseInactiveError(Exception):
    """Raised when database is inactive"""
    pass

class SQLInjectionError(BaseDatabaseError):
    """Raised when potential SQL injection is detected"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            category=DatabaseErrorCategory.PERMISSION_DENIED,
            error_code="SQL_INJECTION",
            details="Potential SQL injection attempt detected"
        )