# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    usuario: str
    area: Optional[str] = None


class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=6)


class UsuarioResponse(UsuarioBase):
    id: int
    rol: str
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    usuario: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioResponse


class MicrosoftAuthResponse(BaseModel):
    """Respuesta de autorización de Microsoft"""
    authorization_url: str
    state: str
