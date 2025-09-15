from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ClienteSchema(BaseModel):
    id: int
    nit: str
    razon_social: str
    contacto_email: Optional[str]
    telefono: Optional[str]
    direccion: Optional[str]
    creado_en: Optional[datetime]

    class Config:
        from_attributes = True
