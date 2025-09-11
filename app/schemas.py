from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, datetime


# ================= CREATE MODELS =================

class ResponsableCreate(BaseModel):
    nombre: str = Field(..., max_length=128)
    email: EmailStr
    area: Optional[str] = Field(None, max_length=50)
    activo: Optional[bool] = True
    role_id: Optional[int] = None


class ProveedorCreate(BaseModel):
    nit: str = Field(..., max_length=20)
    razon_social: Optional[str] = Field(None, max_length=128)
    area: Optional[str] = Field(None, max_length=50)
    contacto_email: Optional[EmailStr]


class FacturaCreate(BaseModel):
    numero_factura: str = Field(..., max_length=50)
    cufe: Optional[str] = Field(None, max_length=128)
    fecha_emision: Optional[date]
    fecha_vencimiento: Optional[date]
    nit_proveedor: str = Field(..., max_length=20)
    razon_social_proveedor: Optional[str] = Field(None, max_length=128)
    nit_cliente: str = Field(..., max_length=20)
    razon_social_cliente: Optional[str] = Field(None, max_length=128)
    subtotal: float = 0.0
    iva: float = 0.0
    total_a_pagar: float = 0.0
    terminos_pago: Optional[str] = Field(None, max_length=20)


class NotificacionCreate(BaseModel):
    factura_id: int
    responsable_id: int
    tipo: str = Field(..., max_length=20)


# ================= SCHEMA MODELS (OUTPUT) =================

class ProveedorSchema(BaseModel):
    id: Optional[int]
    nit: str = Field(..., max_length=20)
    razon_social: Optional[str] = Field(None, max_length=128)
    area: Optional[str] = Field(None, max_length=50)
    contacto_email: Optional[EmailStr]

    class Config:
        orm_mode = True


class ResponsableSchema(BaseModel):
    id: Optional[int]
    nombre: str = Field(..., max_length=128)
    email: EmailStr
    area: Optional[str] = Field(None, max_length=50)
    activo: Optional[bool] = True
    role_id: Optional[int]   # FK hacia tabla roles
    role_nombre: Optional[str]  # Nombre del rol (opcional, para mostrar)

    class Config:
        orm_mode = True


class FacturaSchema(BaseModel):
    id: Optional[int]
    numero_factura: str = Field(..., max_length=50)
    cufe: Optional[str] = Field(None, max_length=128)
    fecha_emision: Optional[date]
    fecha_vencimiento: Optional[date]
    nit_proveedor: str = Field(..., max_length=20)
    razon_social_proveedor: Optional[str] = Field(None, max_length=128)
    nit_cliente: str = Field(..., max_length=20)
    razon_social_cliente: Optional[str] = Field(None, max_length=128)
    subtotal: float = 0.0
    iva: float = 0.0
    total_a_pagar: float = 0.0
    terminos_pago: Optional[str] = Field(None, max_length=20)
    estado_aprobacion: Optional[str] = Field("pendiente", max_length=20)
    fecha_aprobacion: Optional[datetime]
    responsable_id: Optional[int]
    observaciones: Optional[str]
    proveedor_id: Optional[int]

    class Config:
        orm_mode = True


class NotificacionSchema(BaseModel):
    id: Optional[int]
    factura_id: int
    responsable_id: int
    tipo: str = Field(..., max_length=20)
    fecha_envio: Optional[datetime]
    estado: Optional[str] = Field("enviada", max_length=20)

    class Config:
        orm_mode = True
