# services/code_converter.py
import google.generativeai as genai
from logzero import logger
import json
from typing import Dict, Optional
from app.config import settings
from app.schemas.code_converter import CodeConversionRequest
from app.exceptions.code_converter_exceptions import (
    APIKeyNotFoundError,
    ModelNotAvailableError,
    InvalidRequestError,
    ConversionError
)

class CodeConverterService:
    def __init__(self):
        self._setup_gemini()
        
    def _setup_gemini(self):
        """Initialize Gemini API with configuration"""
        try:
            if not settings.GEMINI_API_KEY:
                raise APIKeyNotFoundError("Gemini API key not found in configuration")
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("Gemini API initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API: {str(e)}")
            raise ModelNotAvailableError("Failed to initialize Gemini model")

    def _create_prompt(self, request: CodeConversionRequest) -> str:
        """Create a structured prompt for code conversion"""
        prompt = f"""
        Convert the following {request.source_language.value} code to {request.target_language.value}.
        
        Requirements:
        1. Maintain the same functionality and logic
        2. Follow best practices and idioms of the target language
        3. {'Preserve comments and documentation' if request.preserve_comments else 'Focus on code only'}
        4. {'Add explanatory comments for key changes' if request.add_explanations else ''}
        
        Here's the code to convert:
        
        ```{request.source_language.value}
        {request.source_code}
        ```
        
        Please provide the converted code in the following format:
        ```{request.target_language.value}
        [Your converted code here]
        ```
        
        {'If there are any important differences in implementation or language-specific considerations, please explain them.' if request.add_explanations else ''}
        """
        return prompt

    async def convert_code(self, request: CodeConversionRequest) -> Dict:
        """
        Convert code from source language to target language using Gemini API
        """
        try:
            logger.info(f"Starting code conversion from {request.source_language} to {request.target_language}")
            
            # Create the conversion prompt
            prompt = self._create_prompt(request)
            
            # Generate response from Gemini
            response = await self.model.generate_content_async(prompt)
            
            if not response or not response.text:
                raise ConversionError("No response received from Gemini API")
            
            # Extract code and explanations from response
            converted_code, explanations = self._parse_response(response.text)
            
            if not converted_code:
                raise ConversionError("Failed to extract converted code from response")
            
            result = {
                "converted_code": converted_code,
                "explanations": explanations if request.add_explanations else None
            }
            
            logger.info("Code conversion completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Code conversion failed: {str(e)}")
            if isinstance(e, (APIKeyNotFoundError, ModelNotAvailableError, 
                          InvalidRequestError, ConversionError)):
                raise
            raise ConversionError(f"Failed to convert code: {str(e)}")

    def _parse_response(self, response_text: str) -> tuple[str, Optional[list[str]]]:
        """Parse the response from Gemini to extract code and explanations"""
        try:
            # Split response into code and explanations
            parts = response_text.split("```")
            
            # Extract code (assuming it's in the second code block)
            converted_code = parts[1].strip() if len(parts) > 1 else ""
            
            # Extract explanations (anything after the code block)
            explanations = []
            if len(parts) > 2:
                explanation_text = parts[2].strip()
                if explanation_text:
                    # Split explanations into bullet points or numbered items
                    explanations = [exp.strip() for exp in explanation_text.split('\n')
                                  if exp.strip() and not exp.startswith('```')]
            
            return converted_code, explanations if explanations else None
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {str(e)}")
            raise ConversionError("Failed to parse conversion response")