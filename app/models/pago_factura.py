# app/models/pago_factura.py
"""
Modelo para registro de pagos de facturas.

Mantiene un historial completo y auditable de cada pago realizado.
Una factura puede tener múltiples pagos (parciales o completos).
"""

from sqlalchemy import Column, BigInteger, Numeric, String, Enum, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum
from datetime import datetime
from decimal import Decimal


class EstadoPago(enum.Enum):
    """Estados posibles de un pago"""
    completado = "completado"      # Pago exitoso
    fallido = "fallido"            # Pago rechazado
    cancelado = "cancelado"        # Pago cancelado por usuario


class PagoFactura(Base):
    """
    Registro de pago para una factura.

    Una factura puede tener múltiples pagos (parciales o completos).
    Cada registro es inmutable (auditoría).

    Relación: Factura (1) → PagoFactura (N)
    """
    __tablename__ = "pagos_facturas"

    # ==================== PRIMARY KEY ====================
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Identificador único del pago"
    )

    # ==================== FOREIGN KEYS ====================
    factura_id = Column(
        BigInteger,
        ForeignKey("facturas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Referencia a factura pagada"
    )

    # ==================== DATOS DEL PAGO ====================
    monto_pagado = Column(
        Numeric(15, 2, asdecimal=True),
        nullable=False,
        comment="Cantidad pagada en este registro"
    )

    referencia_pago = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Referencia única: CHEQUE-001, TRF-ABC123, etc"
    )

    metodo_pago = Column(
        String(50),
        nullable=True,
        comment="Método de pago: transferencia, cheque, efectivo"
    )

    estado_pago = Column(
        Enum(EstadoPago),
        default=EstadoPago.completado,
        nullable=False,
        index=True,
        comment="Estado: completado, fallido, cancelado"
    )

    # ==================== AUDITORÍA ====================
    procesado_por = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Email del contador que registró el pago"
    )

    fecha_pago = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Fecha y hora cuando se efectuó el pago"
    )

    # ==================== TIMESTAMPS ====================
    creado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Fecha de creación del registro"
    )

    actualizado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Última actualización"
    )

    # ==================== RELACIÓN ====================
    factura = relationship("Factura", back_populates="pagos")

    # ==================== ÍNDICES COMPUESTOS ====================
    __table_args__ = (
        Index("ix_pagos_facturas_factura_id_estado", "factura_id", "estado_pago"),
        Index("ix_pagos_facturas_fecha_pago", "fecha_pago"),
    )

    def __repr__(self) -> str:
        return f"<PagoFactura(id={self.id}, factura_id={self.factura_id}, monto={self.monto_pagado}, ref={self.referencia_pago})>"
