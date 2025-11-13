# app/models/proveedor.py
"""
Modelo Proveedor - Enterprise Edition

Gestiona proveedores con soporte para:
- Creación manual (interfaz web)
- Creación automática (desde facturas)
- Auditoría completa
- Rastreo de cambios

Autor: Equipo Senior de Desarrollo
Fecha: 2025-11-06
Nivel: Enterprise Fortune 500
"""

from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, text, Index
from sqlalchemy.sql import func
from app.db.base import Base
from sqlalchemy.orm import relationship
from typing import Optional
from datetime import datetime


class Proveedor(Base):
    """
    Modelo de Proveedor con soporte para auto-creación desde facturas.

    Campos principales:
    - id: Identificador único
    - nit: NIT normalizado (XXXXXXXXX-D format)
    - razon_social: Nombre del proveedor
    - contacto_email: Email del proveedor
    - telefono: Teléfono
    - direccion: Dirección
    - area: Área de la empresa
    - activo: Flag activo/inactivo

    Campos de auditoría:
    - creado_en: Timestamp de creación en BD
    - es_auto_creado: Flag que indica si fue auto-creado desde factura
    - creado_automaticamente_en: Timestamp de auto-creación (NULL si manual)

    Relaciones:
    - facturas: One-to-Many con Factura
    """

    __tablename__ = "proveedores"

    # ==================== PRIMARY KEY ====================
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Identificador único del proveedor"
    )

    # ==================== IDENTIFICACIÓN ====================
    nit = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="NIT normalizado en formato XXXXXXXXX-D (ej: 8001854499)"
    )

    razon_social = Column(
        String(255),
        nullable=False,
        comment="Razón social del proveedor"
    )

    # ==================== INFORMACIÓN DE CONTACTO ====================
    area = Column(
        String(100),
        nullable=True,
        comment="Área o departamento de la empresa"
    )

    contacto_email = Column(
        String(255),
        nullable=True,
        comment="Email de contacto principal"
    )

    telefono = Column(
        String(50),
        nullable=True,
        comment="Teléfono de contacto"
    )

    direccion = Column(
        String(255),
        nullable=True,
        comment="Dirección física del proveedor"
    )

    # ==================== ESTADO ====================
    activo = Column(
        Boolean,
        server_default=text("1"),
        nullable=False,
        default=True,
        comment="Flag de estado activo/inactivo"
    )

    # ==================== AUDITORÍA ====================
    creado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp de creación en BD"
    )

    # ==================== AUTO-CREACIÓN (NEW) ====================
    es_auto_creado = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
        index=True,
        comment="Flag indicador: True si fue auto-creado desde factura, False si manual"
    )

    creado_automaticamente_en = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Timestamp exacto de auto-creación desde factura (NULL si manual)"
    )

    # ==================== RELACIONES ====================
    # Relación one-to-many con facturas
    facturas = relationship(
        "Factura",
        back_populates="proveedor",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # ==================== ÍNDICES COMPUESTOS ====================
    # Índice para auditoría de proveedores auto-creados
    __table_args__ = (
        Index(
            'idx_proveedor_auto_creado_fecha',
            'es_auto_creado',
            'creado_automaticamente_en'
        ),
    )

    # ==================== MÉTODOS DE CLASE ====================

    @classmethod
    def crear_automatico(
        cls,
        nit: str,
        razon_social: str,
        email: Optional[str] = None,
        telefono: Optional[str] = None,
        direccion: Optional[str] = None,
        area: Optional[str] = None,
    ) -> "Proveedor":
        """
        Factory method para crear proveedor automáticamente desde factura.

        Args:
            nit: NIT normalizado
            razon_social: Razón social
            email: Email (opcional)
            telefono: Teléfono (opcional)
            direccion: Dirección (opcional)
            area: Área (opcional)

        Returns:
            Instancia de Proveedor con flags de auto-creación

        Nota: No hace commit, el llamador debe manejar la transacción
        """
        return cls(
            nit=nit,
            razon_social=razon_social,
            contacto_email=email,
            telefono=telefono,
            direccion=direccion,
            area=area,
            activo=True,
            es_auto_creado=True,
            creado_automaticamente_en=datetime.utcnow()
        )

    def marcar_como_auto_creado(self) -> None:
        """
        Marca un proveedor como auto-creado.

        Nota: Método de utilidad para casos especiales donde se convierte
        un proveedor manual a auto-creado después de creación.
        """
        self.es_auto_creado = True
        self.creado_automaticamente_en = datetime.utcnow()

    def __repr__(self) -> str:
        """Representación en string del proveedor."""
        origen = "AUTO" if self.es_auto_creado else "MANUAL"
        return f"<Proveedor(id={self.id}, nit={self.nit}, razon_social={self.razon_social}, origen={origen})>"
