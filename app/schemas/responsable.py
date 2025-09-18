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
    role_id: int

class ResponsableRead(ResponsableBase):
    id: int
    activo: bool
    role_id: Optional[int]
    creado_en: Optional[datetime]
    nits: list["ResponsableNitRead"] = []

    class Config:
        from_attributes = True

class ResponsableLogin(BaseModel):
    username: str
    password: str

class ResponsableNitBase(BaseModel):
    nit: str = Field(..., max_length=30)

class ResponsableNitCreate(ResponsableNitBase):
    pass

class ResponsableNitRead(ResponsableNitBase):
    id: int
    responsable_id: int

    class Config:
        from_attributes = True
