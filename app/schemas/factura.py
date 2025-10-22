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


# Schema simple para Responsable anidado
class ResponsableSimple(BaseModel):
    id: int
    nombre: str
    usuario: str

    class Config:
        from_attributes = True


# Base
class FacturaBase(BaseModel):
    numero_factura: str
    fecha_emision: date
    proveedor_id: Optional[int] = None
    subtotal: condecimal(max_digits=15, decimal_places=2)
    iva: condecimal(max_digits=15, decimal_places=2)
    fecha_vencimiento: Optional[date] = None
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
    responsable_id: Optional[int]
    creado_en: datetime
    actualizado_en: Optional[datetime]

    # Relación con proveedor anidado
    proveedor: Optional[ProveedorSimple] = None

    # Relación con responsable anidado (para ADMIN)
    responsable: Optional[ResponsableSimple] = None

    # Campos calculados para compatibilidad con frontend
    nit_emisor: Optional[str] = None
    nombre_emisor: Optional[str] = None
    monto_total: Optional[Decimal] = None

    # Campos de automatización (solo para lectura)
    confianza_automatica: Optional[Decimal] = None
    factura_referencia_id: Optional[int] = None
    motivo_decision: Optional[str] = None
    fecha_procesamiento_auto: Optional[datetime] = None

    # Campos de auditoría - Aprobación/Rechazo (para ADMIN)
    # NOTA: Estos campos vienen desde workflow_aprobacion_facturas vía helpers del modelo
    aprobado_por_workflow: Optional[str] = None
    fecha_aprobacion_workflow: Optional[datetime] = None
    rechazado_por_workflow: Optional[str] = None
    fecha_rechazo_workflow: Optional[datetime] = None
    motivo_rechazo_workflow: Optional[str] = None
    tipo_aprobacion_workflow: Optional[str] = None

    # ✨ ACCION_POR: Leído directamente desde BD (sincronizado automáticamente)
    # Single source of truth - NO SE CALCULA, VIENE DE LA DB
    # Se sincroniza automáticamente en workflow_automatico.py:_sincronizar_estado_factura()
    nombre_responsable: Optional[str] = None
    accion_por: Optional[str] = None
    fecha_accion: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {Decimal: lambda v: str(v)}

    @model_validator(mode='after')
    def populate_calculated_fields(self):
        """Poblar campos calculados desde relaciones (NO incluye accion_por)"""
        # Poblar NIT y nombre desde proveedor
        if self.proveedor:
            self.nit_emisor = self.proveedor.nit
            self.nombre_emisor = self.proveedor.razon_social

        # Calcular monto_total desde total_a_pagar
        if not self.monto_total:
            self.monto_total = self.total_a_pagar

        # Poblar nombre del responsable
        if self.responsable:
            self.nombre_responsable = self.responsable.nombre

        # ✨ ACCION_POR: Ya viene desde la BD sincronizado
        # No se calcula más aquí - se lee directamente del campo factura.accion_por
        # Que fue populado en workflow_automatico.py:_sincronizar_estado_factura()
        # Los campos workflow_history son solo para debugging/auditoría

        # Si accion_por aún no está poblado y es aprobación automática,
        # asignar el valor por defecto (fallback para datos históricos)
        if not self.accion_por and self.estado == EstadoFactura.aprobada_auto:
            self.accion_por = "SISTEMA DE AUTOMATIZACIÓN"

        # Asignar fecha_accion basado en accion_por
        if self.accion_por:
            if self.accion_por == "SISTEMA DE AUTOMATIZACIÓN":
                self.fecha_accion = self.fecha_aprobacion_workflow
            elif self.aprobado_por_workflow == self.accion_por:
                self.fecha_accion = self.fecha_aprobacion_workflow
            elif self.rechazado_por_workflow == self.accion_por:
                self.fecha_accion = self.fecha_rechazo_workflow

        return self
