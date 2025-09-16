# app/schemas/proveedor.py
from pydantic import BaseModel
from typing import Optional

class ProveedorBase(BaseModel):
    nit: str
    razon_social: str
    contacto_email: Optional[str]
    telefono: Optional[str]
    direccion: Optional[str]
    area: Optional[str]

class ProveedorRead(ProveedorBase):
    id: int
    class Config:
    from_attributes = True
