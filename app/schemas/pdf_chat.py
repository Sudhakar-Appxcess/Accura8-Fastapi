# schemas/pdf_chat.py
from pydantic import BaseModel
from typing import List, Dict, Optional

class QueryRequest(BaseModel):
    query: str


class Source(BaseModel):
    page: int
    score: float

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    confidence_score: float