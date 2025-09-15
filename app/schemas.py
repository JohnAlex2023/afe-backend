from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

class RoleSchema(BaseModel):
    id: int
    nombre: str

    class Config:
        from_attributes = True

class ProveedorSchema(BaseModel):
    id: int
    nit: str
    razon_social: str
    area: Optional[str]
    contacto_email: Optional[str]
    telefono: Optional[str]
    direccion: Optional[str]
    creado_en: Optional[datetime]

    class Config:
        from_attributes = True

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

class ResponsableSchema(BaseModel):
    id: int
    usuario: str
    nombre: Optional[str]
    email: str
    area: Optional[str]
    telefono: Optional[str]
    activo: Optional[bool]
    last_login: Optional[datetime]
    role_id: Optional[int]

    class Config:
        from_attributes = True

class FacturaSchema(BaseModel):
    id: int
    numero_factura: str
    fecha_emision: date
    cliente_id: Optional[int]
    proveedor_id: Optional[int]
    subtotal: Optional[float]
    iva: Optional[float]
    total: Optional[float]
    moneda: Optional[str]
    estado: Optional[str]
    fecha_vencimiento: Optional[date]
    observaciones: Optional[str]
    cufe: str
    total_a_pagar: Optional[float]
    responsable_id: Optional[int]
    aprobada_automaticamente: Optional[bool]
    creado_por: Optional[str]
    creado_en: Optional[datetime]
    actualizado_en: Optional[datetime]

    class Config:
        from_attributes = True

class AuditLogSchema(BaseModel):
    id: int
    entidad: str
    entidad_id: int
    accion: str
    usuario: str
    detalle: Optional[dict]
    creado_en: Optional[datetime]

    class Config:
        from_attributes = True

class ResponsableCreate(BaseModel):
    usuario: str
    nombre: Optional[str]
    email: str
    area: Optional[str]
    telefono: Optional[str]
    activo: Optional[bool] = True
    role_id: Optional[int]

class ProveedorCreate(BaseModel):
    nit: str
    razon_social: str
    area: Optional[str]
    contacto_email: Optional[str]
    telefono: Optional[str]
    direccion: Optional[str]

class FacturaCreate(BaseModel):
    numero_factura: str
    fecha_emision: date
    cliente_id: Optional[int]
    proveedor_id: Optional[int]
    subtotal: Optional[float]
    iva: Optional[float]
    total: Optional[float]
    moneda: Optional[str]
    estado: Optional[str] = "pendiente"
    fecha_vencimiento: Optional[date]
    observaciones: Optional[str]
    cufe: str
    total_a_pagar: Optional[float]
    responsable_id: Optional[int]
    aprobada_automaticamente: Optional[bool] = False
    creado_por: Optional[str]