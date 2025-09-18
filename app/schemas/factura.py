# app/schemas/factura.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


#mostrar datos de las facturas
class FacturaBase(BaseModel):
    numero_factura: str
    fecha_emision: date
    cliente_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    subtotal: float
    iva: float
    total: Optional[float] = None
    moneda: Optional[str] = "COP"
    fecha_vencimiento: Optional[date] = None
    observaciones: Optional[str] = None
    cufe: str
    total_a_pagar: Optional[float] = None

class FacturaCreate(FacturaBase):
    pass

class FacturaRead(FacturaBase):
    id: int
    estado: str
    aprobada_automaticamente: Optional[bool] = None  
    responsable_id: Optional[int]
    creado_en: datetime
    actualizado_en: Optional[datetime]

    class Config:
        from_attributes = True

