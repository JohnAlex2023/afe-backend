# app/schemas/cliente.py
from pydantic import BaseModel
from typing import Optional

class ClienteBase(BaseModel):
    nit: str
    razon_social: str
    contacto_email: Optional[str]
    telefono: Optional[str]
    direccion: Optional[str]

class ClienteRead(ClienteBase):
    id: int
    class Config:
        from_attributes = True
