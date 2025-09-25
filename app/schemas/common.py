from pydantic import BaseModel
from typing import Any, Optional

class ErrorResponse(BaseModel):
    detail: str

class ResponseBase(BaseModel):
    """Esquema base para respuestas de la API"""
    success: bool
    message: str
    data: Optional[Any] = None
