"""
Modelo de Grupo (Sede/Empresa) para clasificación de facturas por grupos.

Permite aislar datos por grupos de responsables:
- Cada grupo es una sede u empresa
- Un responsable puede estar en múltiples grupos
- Un NIT puede estar en múltiples grupos con diferentes responsables
- Las facturas pertenecen a un grupo específico

Nivel: Enterprise Multi-Tenant Architecture
"""

from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Text, JSON, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime


class Grupo(Base):
    """
    Grupo o Sede empresarial.

    Representa una unidad de negocio separada (Avidanti, Soacha, etc.).
    Las facturas pertenecen a un grupo, los responsables pueden estar en múltiples grupos.

    Campos:
    - id: Identificador único
    - nombre: Nombre del grupo (Avidanti, Soacha, etc.)
    - descripcion: Descripción detallada del grupo
    - correos_corporativos: JSON array de correos corporativos para identificar facturas
    - activo: Flag de estado activo/inactivo
    - creado_en: Timestamp de creación
    - actualizado_en: Timestamp de última actualización
    """

    __tablename__ = "grupos"

    # ==================== PRIMARY KEY ====================
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Identificador único del grupo"
    )

    # ==================== IDENTIFICACIÓN ====================
    nombre = Column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
        comment="Nombre del grupo/sede (Avidanti, Soacha, etc.)"
    )

    descripcion = Column(
        Text,
        nullable=True,
        comment="Descripción detallada del grupo"
    )

    # ==================== CORREOS CORPORATIVOS ====================
    # Array JSON de correos asociados al grupo
    # Usado para identificar automáticamente a qué grupo pertenece una factura
    # Ejemplo: ["avidanti@corp.com", "info@avidanti.co"]
    correos_corporativos = Column(
        JSON,
        nullable=True,
        default=list,
        comment="Array de correos corporativos del grupo para identificar facturas"
    )

    # ==================== ESTADO ====================
    activo = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
        comment="Flag de estado activo/inactivo"
    )

    # ==================== AUDITORÍA ====================
    creado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp de creación"
    )

    actualizado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp de última actualización"
    )

    # ==================== RELACIONES ====================
    # Relación M:N con Responsable
    responsables = relationship(
        "ResponsableGrupo",
        back_populates="grupo",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Relación con facturas
    facturas = relationship(
        "Factura",
        back_populates="grupo",
        lazy="select"
    )

    # Relación con asignaciones NIT
    asignaciones_nit = relationship(
        "AsignacionNitResponsable",
        back_populates="grupo",
        lazy="select"
    )

    # ==================== ÍNDICES ====================
    __table_args__ = (
        Index('idx_grupo_activo', 'activo'),
        Index('idx_grupo_nombre', 'nombre'),
    )

    def __repr__(self) -> str:
        return f"<Grupo(id={self.id}, nombre={self.nombre}, activo={self.activo})>"


class ResponsableGrupo(Base):
    """
    Tabla relacional M:N entre Responsable y Grupo.

    Define la relación entre responsables y grupos:
    - Un responsable puede estar en múltiples grupos
    - Un grupo puede tener múltiples responsables
    - Cada responsable tiene un rol específico en cada grupo

    Campos:
    - responsable_id: FK a responsables
    - grupo_id: FK a grupos
    - activo: Flag de estado (soft delete)
    - creado_en: Timestamp de creación
    """

    __tablename__ = "responsable_grupo"

    # ==================== PRIMARY KEY ====================
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Identificador único"
    )

    # ==================== FOREIGN KEYS ====================
    responsable_id = Column(
        BigInteger,
        nullable=False,
        index=True,
        comment="FK a responsables"
    )

    grupo_id = Column(
        BigInteger,
        nullable=False,
        index=True,
        comment="FK a grupos"
    )

    # ==================== ESTADO ====================
    activo = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="Flag de pertenencia activa"
    )

    # ==================== AUDITORÍA ====================
    creado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp de creación"
    )

    # ==================== RELACIONES ====================
    grupo = relationship("Grupo", back_populates="responsables", foreign_keys=[grupo_id])
    responsable = relationship("Responsable", back_populates="grupos", foreign_keys=[responsable_id])

    # ==================== CONSTRAINTS ====================
    __table_args__ = (
        UniqueConstraint('responsable_id', 'grupo_id', name='uq_responsable_grupo'),
        Index('idx_responsable_grupo_grupo', 'grupo_id'),
        Index('idx_responsable_grupo_responsable', 'responsable_id'),
    )

    def __repr__(self) -> str:
        return f"<ResponsableGrupo(responsable_id={self.responsable_id}, grupo_id={self.grupo_id}, activo={self.activo})>"
