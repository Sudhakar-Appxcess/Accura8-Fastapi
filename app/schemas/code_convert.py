from pydantic import BaseModel
from typing import Optional,Union, Dict
class CodeConvertRequest(BaseModel):
    source_code: str
    source_language: str
    target_language: str

class StandardResponse(BaseModel):
    status: bool
    message: str
    # data: Optional[dict] = None
    data: Optional[Union[Dict, str]] = None