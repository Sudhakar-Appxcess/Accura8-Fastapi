# services/sql_migration.py
from logzero import logger
import google.generativeai as genai
from typing import Dict, Optional
from app.config import settings
from app.schemas.sql_migration import SQLMigrationRequest
from app.exceptions.sql_migration_exceptions import SQLMigrationError, InvalidSQLError

class SQLMigrationService:
    def __init__(self):
        self._setup_gemini()
        
    def _setup_gemini(self):
        try:
            if not settings.GEMINI_API_KEY:
                raise SQLMigrationError("Gemini API key not found")
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("Gemini API initialized for SQL migration")
            
        except Exception as e:
            logger.error(f"Gemini API initialization failed: {str(e)}")
            raise SQLMigrationError("Failed to initialize SQL migration service")

    def _create_prompt(self, request: SQLMigrationRequest) -> str:
        return f"""
        Convert the following {request.source_db.value} SQL query to {request.target_db.value} syntax.
        
        Requirements:
        1. Maintain identical functionality and logic
        2. Follow {request.target_db.value} best practices
        3. Handle syntax differences and specific features
        4. {'Preserve comments and formatting' if request.preserve_comments else 'Focus on query only'}
        5. {'Add explanations for key changes' if request.add_explanations else ''}
        
        Source Query ({request.source_db.value}):
        ```sql
        {request.sql_query}
        ```
        
        Please provide the converted query in this format:
        ```sql
        [Converted query here]
        ```
        
        {'Please explain any important syntax differences or implementation considerations.' if request.add_explanations else ''}
        """

    async def migrate_sql(self, request: SQLMigrationRequest) -> Dict:
        """
        Migrate SQL query from source to target database using Gemini
        """
        try:
            logger.info(f"Starting SQL migration from {request.source_db} to {request.target_db}")
            
            prompt = self._create_prompt(request)
            response = await self.model.generate_content_async(prompt)
            
            if not response or not response.text:
                raise SQLMigrationError("No response from Gemini API")
            
            converted_query, explanations = self._parse_response(response.text)
            
            if not converted_query:
                raise SQLMigrationError("Failed to extract converted query")
            
            result = {
                "converted_query": converted_query,
                "explanations": explanations if request.add_explanations else None
            }
            
            logger.info("SQL migration completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"SQL migration failed: {str(e)}")
            if isinstance(e, SQLMigrationError):
                raise
            raise SQLMigrationError(f"Failed to migrate SQL: {str(e)}")

    def _parse_response(self, response_text: str) -> tuple[str, Optional[list[str]]]:
        """Parse Gemini response to extract query and explanations"""
        try:
            parts = response_text.split("```")
            converted_query = parts[1].strip() if len(parts) > 1 else ""
            
            explanations = []
            if len(parts) > 2:
                explanation_text = parts[2].strip()
                if explanation_text:
                    explanations = [exp.strip() for exp in explanation_text.split('\n')
                                  if exp.strip() and not exp.startswith('```')]
            
            return converted_query, explanations if explanations else None
            
        except Exception as e:
            logger.error(f"Failed to parse migration response: {str(e)}")
            raise SQLMigrationError("Failed to parse migration response")