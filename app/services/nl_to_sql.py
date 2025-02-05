
# services/nl_to_sql.py
from logzero import logger
import google.generativeai as genai
from typing import Dict, Optional
from app.config import settings
from app.schemas.nl_to_sql import NLToSQLRequest
from app.exceptions.nl_to_sql_exceptions import NLToSQLError

class NLToSQLService:
    def __init__(self):
        self._setup_gemini()

    def _setup_gemini(self):
        try:
            if not settings.GEMINI_API_KEY:
                raise NLToSQLError("Gemini API key not found")
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("Gemini API initialized for NL to SQL conversion")
            
        except Exception as e:
            logger.error(f"Gemini API initialization failed: {str(e)}")
            raise NLToSQLError("Failed to initialize NL to SQL service")

    def _create_prompt(self, request: NLToSQLRequest) -> str:
        schema_info = ""
        if request.table_schema:
            schema_info = "\nDatabase Schema:\n"
            for table, columns in request.table_schema.items():
                schema_info += f"\nTable: {table}\nColumns: {', '.join(columns)}"

        return f"""
        Convert this natural language question to a {request.db_type.value} SQL query:
        
        Question: {request.question}
        {schema_info}
        
        Requirements:
        1. Generate valid {request.db_type.value} SQL syntax
        2. Use proper table joins if needed
        3. Include appropriate WHERE conditions
        4. Follow SQL best practices
        5. {'Add explanations for the query structure' if request.add_explanations else ''}
        
        Provide the SQL query in this format:
        ```sql
        [SQL query here]
        ```
        
        {'Also explain the query structure and any assumptions made.' if request.add_explanations else ''}
        """

    async def convert_to_sql(self, request: NLToSQLRequest) -> Dict:
        try:
            logger.info(f"Converting natural language to {request.db_type} SQL")
            
            prompt = self._create_prompt(request)
            response = await self.model.generate_content_async(prompt)
            
            if not response or not response.text:
                raise NLToSQLError("No response from Gemini API")
            
            sql_query, explanations = self._parse_response(response.text)
            
            if not sql_query:
                raise NLToSQLError("Failed to generate SQL query")
            
            # Calculate confidence score based on response quality
            confidence_score = self._calculate_confidence(sql_query, request)
            
            result = {
                "sql_query": sql_query,
                "explanations": explanations if request.add_explanations else None,
                "confidence_score": confidence_score
            }
            
            logger.info("Natural language to SQL conversion completed")
            return result
            
        except Exception as e:
            logger.error(f"NL to SQL conversion failed: {str(e)}")
            if isinstance(e, NLToSQLError):
                raise
            raise NLToSQLError(f"Failed to convert to SQL: {str(e)}")

    def _parse_response(self, response_text: str) -> tuple[str, Optional[list[str]]]:
        try:
            parts = response_text.split("```")
            sql_query = parts[1].strip() if len(parts) > 1 else ""
            
            explanations = []
            if len(parts) > 2:
                explanation_text = parts[2].strip()
                if explanation_text:
                    explanations = [exp.strip() for exp in explanation_text.split('\n')
                                  if exp.strip() and not exp.startswith('```')]
            
            return sql_query, explanations if explanations else None
            
        except Exception as e:
            logger.error(f"Failed to parse conversion response: {str(e)}")
            raise NLToSQLError("Failed to parse conversion response")

    def _calculate_confidence(self, sql_query: str, request: NLToSQLRequest) -> float:
        """Calculate confidence score for the generated SQL"""
        score = 1.0
        
        # Basic validation checks
        if not sql_query.strip():
            return 0.0
            
        # Check SQL keywords
        if not any(keyword in sql_query.upper() for keyword in ['SELECT', 'FROM']):
            score *= 0.5
            
        # Schema validation if provided
        if request.table_schema:
            tables = list(request.table_schema.keys())
            if not any(table.lower() in sql_query.lower() for table in tables):
                score *= 0.7
                
        return round(max(min(score, 1.0), 0.0), 2)
