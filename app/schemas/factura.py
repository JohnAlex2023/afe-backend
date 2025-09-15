from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class FacturaSchema(BaseModel):
    id: int
    numero_factura: str
    cufe: str

    # Fechas
    fecha_emision: date
    fecha_vencimiento: Optional[date]

    # Relaciones
    cliente_id: int
    proveedor_id: int
    responsable_id: Optional[int]

    # Montos
    subtotal: float
    iva: float
    total: Optional[float]        # 👈 aquí el cambio
    total_a_pagar: Optional[float]

    # Estado y control
    estado: str
    aprobada_automaticamente: bool

    # Auditoría
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        from_attributes = True
