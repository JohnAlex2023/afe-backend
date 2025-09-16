# app/schemas/responsable.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class ResponsableBase(BaseModel):
    usuario: str = Field(..., example="juan.perez@empresa.com")
    email: EmailStr
    nombre: Optional[str]

class ResponsableCreate(ResponsableBase):
    password: str = Field(..., min_length=8)

class ResponsableRead(ResponsableBase):
    id: int
    activo: bool
    role_id: Optional[int]
    creado_en: Optional[datetime]

    class Config:
    from_attributes = True

class ResponsableLogin(BaseModel):
    username: str
    password: str
