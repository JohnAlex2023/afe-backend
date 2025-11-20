# app/schemas/pago.py
"""
Schemas para manejo de pagos de facturas.

Validaciones y estructuras de datos para registro y consulta de pagos.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class PagoRequest(BaseModel):
    """
    Request para registrar un pago de factura.

    Campos requeridos:
    - monto_pagado: Cantidad a pagar (debe ser > 0)
    - referencia_pago: Identificador único (cheque, transferencia, etc)

    Campos opcionales:
    - metodo_pago: Tipo de pago (transferencia, cheque, efectivo)
    """
    monto_pagado: Decimal = Field(..., gt=0, decimal_places=2, description="Cantidad pagada")
    referencia_pago: str = Field(..., min_length=3, max_length=100, description="Referencia única: CHQ-001, TRF-ABC")
    metodo_pago: Optional[str] = Field(None, max_length=50, description="Método: transferencia, cheque, efectivo")

    @validator('monto_pagado')
    def monto_valido(cls, v):
        """Validar que el monto sea positivo"""
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v

    @validator('referencia_pago')
    def ref_no_vacia(cls, v):
        """Validar que la referencia no sea solo espacios"""
        if not v or not v.strip():
            raise ValueError("Referencia no puede estar vacía")
        return v.strip().upper()


class PagoResponse(BaseModel):
    """
    Response: Datos de un pago registrado.
    """
    id: int
    factura_id: int
    monto_pagado: Decimal
    referencia_pago: str
    metodo_pago: Optional[str]
    estado_pago: str
    procesado_por: str
    fecha_pago: datetime

    class Config:
        from_attributes = True


class FacturaConPagosResponse(BaseModel):
    """
    Response: Factura con datos de pagos sincronizados.

    Incluye información de la factura y detalles de pagos completados.
    """
    id: int
    numero_factura: str
    estado: str
    total_calculado: Decimal
    total_pagado: Decimal
    pendiente_pagar: Decimal
    esta_completamente_pagada: bool
    pagos: List[PagoResponse]

    class Config:
        from_attributes = True
