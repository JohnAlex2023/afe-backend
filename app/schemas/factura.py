from pydantic import BaseModel, condecimal, model_validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class EstadoFactura(str, Enum):
    pendiente = "pendiente"
    en_revision = "en_revision"
    aprobada = "aprobada"
    rechazada = "rechazada"
    aprobada_auto = "aprobada_auto"


# Schema simple para Proveedor anidado
class ProveedorSimple(BaseModel):
    id: int
    nit: str
    razon_social: str

    class Config:
        from_attributes = True


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
    
    # ✨ CAMPOS PARA AUTOMATIZACIÓN (opcionales en creación)
    concepto_principal: Optional[str] = None
    concepto_normalizado: Optional[str] = None
    concepto_hash: Optional[str] = None
    tipo_factura: Optional[str] = None
    items_resumen: Optional[List[Dict[str, Any]]] = None
    orden_compra_numero: Optional[str] = None
    orden_compra_sap: Optional[str] = None
    notas_adicionales: Optional[Dict[str, Any]] = None

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

    # Relación con proveedor anidado
    proveedor: Optional[ProveedorSimple] = None

    # Campos calculados para compatibilidad con frontend
    nit_emisor: Optional[str] = None
    nombre_emisor: Optional[str] = None
    monto_total: Optional[Decimal] = None

    # Campos de automatización (solo para lectura)
    patron_recurrencia: Optional[str] = None
    confianza_automatica: Optional[Decimal] = None
    factura_referencia_id: Optional[int] = None
    motivo_decision: Optional[str] = None
    procesamiento_info: Optional[Dict[str, Any]] = None
    fecha_procesamiento_auto: Optional[datetime] = None
    version_algoritmo: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {Decimal: lambda v: str(v)}

    @model_validator(mode='after')
    def populate_calculated_fields(self):
        """Poblar campos calculados desde relaciones"""
        # Poblar NIT y nombre desde proveedor
        if self.proveedor:
            self.nit_emisor = self.proveedor.nit
            self.nombre_emisor = self.proveedor.razon_social

        # Calcular monto_total desde total o total_a_pagar
        if not self.monto_total:
            self.monto_total = self.total or self.total_a_pagar

        return self
