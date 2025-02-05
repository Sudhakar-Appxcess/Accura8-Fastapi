# schemas/code_converter.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from enum import Enum

class ProgrammingLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    PHP = "php"
    RUBY = "ruby"
    GO = "go"
    RUST = "rust"
    SWIFT = "swift"
    KOTLIN = "kotlin"

class CodeConversionRequest(BaseModel):
    source_code: str = Field(..., min_length=1, max_length=10000)
    source_language: ProgrammingLanguage
    target_language: ProgrammingLanguage
    preserve_comments: Optional[bool] = True
    add_explanations: Optional[bool] = False

    @validator('source_code')
    def validate_source_code(cls, v):
        if not v.strip():
            raise ValueError('Source code cannot be empty or just whitespace')
        return v

    @validator('target_language')
    def validate_target_language(cls, v, values):
        if 'source_language' in values and v == values['source_language']:
            raise ValueError('Source and target languages must be different')
        return v

class StandardResponse(BaseModel):
    status: bool
    message: str
    data: Optional[dict] = None

class CodeConversionResponse(StandardResponse):
    data: dict = {
        "converted_code": str,
        "explanations": Optional[list[str]] 
    }