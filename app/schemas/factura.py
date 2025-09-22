from pydantic import BaseModel, condecimal
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class EstadoFactura(str, Enum):
    pendiente = "pendiente"
    en_revision = "en_revision"
    aprobada = "aprobada"
    rechazada = "rechazada"
    aprobada_auto = "aprobada_auto"


# Base
class FacturaBase(BaseModel):
    numero_factura: str
    fecha_emision: date
    cliente_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    subtotal: condecimal(max_digits=15, decimal_places=2)
    iva: condecimal(max_digits=15, decimal_places=2)
    total: Optional[condecimal(max_digits=15, decimal_places=2)] = None
    moneda: str = "COP"
    fecha_vencimiento: Optional[date] = None
    observaciones: Optional[str] = None
    cufe: str
    total_a_pagar: Optional[condecimal(max_digits=15, decimal_places=2)] = None

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


# Para crear
class FacturaCreate(FacturaBase):
    pass


# Para leer
class FacturaRead(FacturaBase):
    id: int
    estado: EstadoFactura
    aprobada_automaticamente: Optional[bool] = None
    responsable_id: Optional[int]
    creado_en: datetime
    actualizado_en: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {Decimal: lambda v: str(v)}
