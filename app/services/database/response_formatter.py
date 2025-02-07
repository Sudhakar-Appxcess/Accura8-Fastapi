from typing import Dict, List, Any
import json
import io
import csv
from decimal import Decimal
from datetime import datetime, date
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from logzero import logger

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects"""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)

class DatabaseResponseFormatter:
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self.LARGE_RESULT_THRESHOLD = 20

    async def format_response(self, query_results: Dict[str, Any]) -> Dict[str, Any]:
        """Format database query results for user-friendly presentation"""
        results = query_results["results"]
        row_count = query_results["row_count"]
        execution_time = query_results["execution_time"]

        if row_count == 0:
            return {
                "summary": "No results found for your query.",
                "execution_time": execution_time
            }

        if row_count > self.LARGE_RESULT_THRESHOLD:
            summary = await self._generate_summary(results[:5], is_sample=True)
            return self._create_large_response(
                summary, results, execution_time, row_count
            )
        else:
            natural_language = await self._generate_natural_language(results)
            return self._create_small_response(
                natural_language, execution_time, row_count
            )

    async def _generate_summary(self, data: List[Dict[str, Any]], is_sample: bool = False) -> str:
        """Generate summary for large result sets"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a data analyst providing clear, informative summaries. "
                        "Focus on key patterns and insights. Use clear, professional language."
                    )
                },
                {
                    "role": "user",
                    "content": f"""
                        Analyze these database query results and provide a summary:
                        Data: {json.dumps(data, cls=DecimalEncoder, indent=2)}
                        
                        Create a summary that:
                        1. Provides an overview of the data type and content
                        2. Highlights key patterns or trends
                        3. Mentions notable statistics or findings
                        4. {"Notes this is based on a sample of the full dataset" if is_sample else ""}
                        
                        Format the response to be clear and professional, using bold for key terms 
                        and proper sentence structure. Do not include technical details or raw numbers 
                        unless they are significant findings.
                    """
                }
            ]
            
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=250
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return "Unable to generate summary. Please check the data directly."

    async def _generate_natural_language(self, data: List[Dict[str, Any]]) -> str:
        """Generate detailed natural language description for small result sets"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a data interpreter converting database results into clear, "
                        "natural language. Present all information in a readable, organized format. "
                        "Use appropriate formatting for clarity and emphasis."
                    )
                },
                {
                    "role": "user",
                    "content": f"""
                        Convert this data into natural language:
                        {json.dumps(data, cls=DecimalEncoder, indent=2)}
                        
                        Rules for the response:
                        1. Present each record in clear, complete sentences
                        2. Use bold formatting for key fields and values
                        3. Maintain all precise numeric values and dates
                        4. Organize information logically
                        5. Include all data points but avoid technical language
                        6. Make relationships between data points clear
                        7. Use proper sentence structure and transitions
                        
                        The response should be detailed but readable, highlighting important information 
                        while maintaining accuracy of all values.
                    """
                }
            ]
            
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating natural language: {str(e)}")
            return "Unable to generate natural language description. Please check the raw data."

    def _create_large_response(
        self, 
        summary: str, 
        results: List[Dict[str, Any]], 
        execution_time: float,
        row_count: int
    ) -> Dict[str, Any]:
        """Create response for large result sets with CSV download"""
        try:
            output = io.StringIO()
            if results:
                writer = csv.DictWriter(output, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
            
            csv_bytes = output.getvalue().encode('utf-8')
            bytes_io = io.BytesIO(csv_bytes)
            
            return {
                "summary": summary,
                "execution_time": execution_time,
                "row_count": row_count,
                "file_download": StreamingResponse(
                    bytes_io,
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": "attachment; filename=query_results.csv"
                    }
                )
            }
        except Exception as e:
            logger.error(f"Error creating CSV response: {str(e)}")
            return {
                "summary": summary,
                "execution_time": execution_time,
                "row_count": row_count,
                "error": "Failed to create CSV file"
            }
        
    def _create_small_response(
        self, 
        natural_language: str, 
        execution_time: float,
        row_count: int
    ) -> Dict[str, Any]:
        """Create response for small result sets"""
        return {
            "natural_language": natural_language,
            "execution_time": execution_time,
            "row_count": row_count
        }