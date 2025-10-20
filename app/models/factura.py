# app/models/factura.py
from sqlalchemy import Column, BigInteger, String, Date, Numeric, Enum, Boolean, ForeignKey, DateTime, UniqueConstraint, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class EstadoFactura(enum.Enum):
    pendiente = "pendiente"
    en_revision = "en_revision"
    aprobada = "aprobada"
    rechazada = "rechazada"
    aprobada_auto = "aprobada_auto"
    pagada = "pagada"

class Factura(Base):
    __tablename__ = "facturas"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    numero_factura = Column(String(50), nullable=False)
    fecha_emision = Column(Date, nullable=False)
    proveedor_id = Column(BigInteger, ForeignKey("proveedores.id"), nullable=True)
    subtotal = Column(Numeric(15, 2, asdecimal=True))
    iva = Column(Numeric(15, 2, asdecimal=True))
    estado = Column(Enum(EstadoFactura), default=EstadoFactura.pendiente, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)
    cufe = Column(String(100), unique=True, nullable=False)
    total_a_pagar = Column(Numeric(15, 2, asdecimal=True))
    responsable_id = Column(BigInteger, ForeignKey("responsables.id"), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ✨ CAMPOS PARA APROBACIÓN/RECHAZO MANUAL ✨
    aprobado_por = Column(String(100), nullable=True,
                         comment="Usuario que aprobó la factura manualmente")
    fecha_aprobacion = Column(DateTime(timezone=True), nullable=True,
                             comment="Fecha y hora de aprobación")
    rechazado_por = Column(String(100), nullable=True,
                          comment="Usuario que rechazó la factura")
    fecha_rechazo = Column(DateTime(timezone=True), nullable=True,
                          comment="Fecha y hora de rechazo")
    motivo_rechazo = Column(String(1000), nullable=True,
                           comment="Motivo del rechazo de la factura")
    
    # ✨ CAMPOS PARA AUTOMATIZACIÓN DE FACTURAS RECURRENTES ✨

    # Automatización inteligente
    confianza_automatica = Column(Numeric(3, 2), nullable=True,
                                 comment="Confianza (0.00-1.00) para aprobación automática")
    factura_referencia_id = Column(BigInteger, ForeignKey("facturas.id"), nullable=True,
                                  comment="ID de factura del mes anterior usada como referencia")
    motivo_decision = Column(String(500), nullable=True,
                           comment="Razón de la decisión automática")

    # Metadata y auditoría
    fecha_procesamiento_auto = Column(DateTime(timezone=True), nullable=True,
                                     comment="Cuándo se ejecutó el procesamiento automático")

    # ✨ CAMPOS PARA MATCHING Y COMPARACIÓN EMPRESARIAL ✨

    # Concepto y descripción
    concepto_principal = Column(String(500), nullable=True,
                               comment="Descripción/concepto principal de la factura")
    concepto_hash = Column(String(32), nullable=True, index=True,
                          comment="Hash MD5 del concepto normalizado para matching rápido")
    concepto_normalizado = Column(String(500), nullable=True,
                                 comment="Concepto sin stopwords y normalizado")

    # Orden de compra
    orden_compra_numero = Column(String(50), nullable=True, index=True,
                                comment="Número de orden de compra asociada")

    # Patrón de recurrencia
    patron_recurrencia = Column(String(20), nullable=True,
                               comment="Patrón: FIJO, VARIABLE, UNICO, DESCONOCIDO")

    # Tipo de factura (clasificación empresarial)
    tipo_factura = Column(String(20), nullable=False, server_default='COMPRA',
                         comment="Tipo: COMPRA, VENTA, NOTA_CREDITO, NOTA_DEBITO")

    proveedor = relationship("Proveedor", back_populates="facturas", lazy="joined")
    responsable = relationship("Responsable", back_populates="facturas", lazy="joined")

    # Relationship para factura de referencia (para automatización)
    factura_referencia = relationship("Factura", remote_side=[id], backref="facturas_relacionadas")

    # ✨ NUEVA RELACIÓN: Items de la factura (líneas individuales)
    items = relationship(
        "FacturaItem",
        back_populates="factura",
        lazy="selectin",  # Carga eficiente de items
        cascade="all, delete-orphan",  # Si se borra factura, se borran items
        order_by="FacturaItem.numero_linea"  # Ordenados por línea
    )

    # ✨ FASE 2: Relación a Workflow (para normalización de datos)
    workflow_history = relationship(
        "WorkflowAprobacionFactura",
        foreign_keys="[WorkflowAprobacionFactura.factura_id]",
        uselist=False,  # Solo un workflow por factura
        lazy="select",  # Carga bajo demanda
        viewonly=True   # No modifica desde Factura
    )

    __table_args__ = (UniqueConstraint("numero_factura", "proveedor_id", name="uix_num_prov"),)

    # ==================== COMPUTED PROPERTIES (FASE 1 - PROFESIONAL) ====================

    @property
    def total_calculado(self):
        """
        Total calculado dinámicamente desde subtotal + IVA.

        ⚠️ DEPRECATION NOTICE:
        El campo 'total_a_pagar' almacenado en DB está marcado para eliminación.
        Usar esta propiedad garantiza siempre el valor correcto.

        Nivel: Fortune 500 Data Integrity
        """
        from decimal import Decimal
        subtotal = self.subtotal or Decimal('0.00')
        iva = self.iva or Decimal('0.00')
        return subtotal + iva

    @property
    def total_desde_items(self):
        """
        Total calculado desde la suma de items individuales.

        Útil para validación y detección de inconsistencias.
        Si total_calculado != total_desde_items, hay un problema de integridad.

        Returns:
            Decimal: Suma de total de todos los items
        """
        from decimal import Decimal
        if not self.items:
            return Decimal('0.00')
        return sum((item.total or Decimal('0.00')) for item in self.items)

    @property
    def tiene_inconsistencia_total(self):
        """
        Detecta si hay inconsistencia entre total almacenado vs calculado.

        Returns:
            bool: True si hay inconsistencia que requiere corrección
        """
        from decimal import Decimal
        if self.total_a_pagar is None:
            return False

        diferencia = abs(self.total_a_pagar - self.total_calculado)
        # Tolerancia de 1 centavo por redondeo
        return diferencia > Decimal('0.01')

    # ==================== HELPERS DE WORKFLOW (FASE 2 - NORMALIZACIÓN) ====================

    @property
    def aprobado_por_workflow(self):
        """
        Usuario que aprobó la factura (desde workflow si existe, sino desde campo legacy).

        ⚠️ DEPRECATION NOTICE:
        El campo 'aprobado_por' en facturas será eliminado en Fase 2.4
        Usar esta propiedad garantiza acceso al dato correcto.

        Nivel: Fortune 500 Data Normalization
        """
        # Primero intentar desde workflow (fuente primaria)
        if self.workflow_history and self.workflow_history.aprobada_por:
            return self.workflow_history.aprobada_por

        # Fallback a campo legacy en facturas
        return self.aprobado_por

    @property
    def fecha_aprobacion_workflow(self):
        """Fecha de aprobación (desde workflow primero, sino desde campo legacy)."""
        if self.workflow_history and self.workflow_history.fecha_aprobacion:
            return self.workflow_history.fecha_aprobacion
        return self.fecha_aprobacion

    @property
    def rechazado_por_workflow(self):
        """Usuario que rechazó (desde workflow primero, sino desde campo legacy)."""
        if self.workflow_history and self.workflow_history.rechazada_por:
            return self.workflow_history.rechazada_por
        return self.rechazado_por

    @property
    def fecha_rechazo_workflow(self):
        """Fecha de rechazo (desde workflow primero, sino desde campo legacy)."""
        if self.workflow_history and self.workflow_history.fecha_rechazo:
            return self.workflow_history.fecha_rechazo
        return self.fecha_rechazo

    @property
    def motivo_rechazo_workflow(self):
        """Motivo de rechazo (desde workflow primero, sino desde campo legacy)."""
        if self.workflow_history and self.workflow_history.detalle_rechazo:
            return self.workflow_history.detalle_rechazo
        return self.motivo_rechazo

    @property
    def tipo_aprobacion_workflow(self):
        """
        Tipo de aprobación (solo disponible en workflow).

        Returns:
            str: 'automatica', 'manual', 'masiva', 'forzada' o None
        """
        if self.workflow_history and self.workflow_history.tipo_aprobacion:
            return self.workflow_history.tipo_aprobacion.value
        return None
