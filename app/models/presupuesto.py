"""
Modelos de datos para sistema de control presupuestal empresarial.

Arquitectura de 3 capas:
1. Planeación: lineas_presupuesto (presupuesto planeado)
2. Ejecución: ejecuciones_presupuestales (vinculación presupuesto ↔ facturas)
3. Realidad: facturas (facturas reales de DIAN)

Nivel: Fortune 500 Enterprise
Autor: Backend AFE - Sistema de Control Presupuestal
Fecha: 2025-10-04
"""

from sqlalchemy import (
    Column, BigInteger, String, DateTime, Numeric, Text,
    Enum, JSON, Boolean, ForeignKey, UniqueConstraint, CheckConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum


# ==================== ENUMS ====================

class TipoLineaPresupuesto(enum.Enum):
    """Tipos de línea presupuestal."""
    OPEX = "opex"  # Gastos operacionales
    CAPEX = "capex"  # Inversión de capital
    SERVICIOS = "servicios"  # Servicios
    LICENCIAS = "licencias"  # Licencias de software
    MANTENIMIENTO = "mantenimiento"  # Mantenimiento
    CONSULTORIA = "consultoria"  # Consultoría


class EstadoLineaPresupuesto(enum.Enum):
    """Estados de una línea presupuestal."""
    BORRADOR = "borrador"
    APROBADO = "aprobado"
    ACTIVO = "activo"
    SUSPENDIDO = "suspendido"
    CERRADO = "cerrado"
    CANCELADO = "cancelado"


class EstadoEjecucion(enum.Enum):
    """Estados de ejecución presupuestal."""
    PENDIENTE_VINCULACION = "pendiente_vinculacion"
    VINCULADO = "vinculado"
    PENDIENTE_APROBACION = "pendiente_aprobacion"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    OBSERVADO = "observado"


class TipoDesviacion(enum.Enum):
    """Tipos de desviación presupuestal."""
    DENTRO_RANGO = "dentro_rango"  # <= 5%
    BAJO_PRESUPUESTO = "bajo_presupuesto"  # Gastó menos
    SOBRE_PRESUPUESTO_LEVE = "sobre_presupuesto_leve"  # 5-15%
    SOBRE_PRESUPUESTO_MODERADO = "sobre_presupuesto_moderado"  # 15-25%
    SOBRE_PRESUPUESTO_CRITICO = "sobre_presupuesto_critico"  # > 25%


class NivelAprobacion(enum.Enum):
    """Niveles de aprobación requeridos."""
    RESPONSABLE_LINEA = "responsable_linea"  # Aprobación del responsable
    JEFE_AREA = "jefe_area"  # Jefe de área
    GERENCIA_FINANCIERA = "gerencia_financiera"  # Gerencia financiera
    GERENCIA_GENERAL = "gerencia_general"  # Gerencia general
    CFO = "cfo"  # CFO
    CEO = "ceo"  # CEO (solo casos críticos)


class TipoAlerta(enum.Enum):
    """Tipos de alerta del sistema."""
    DESVIACION_PRESUPUESTAL = "desviacion_presupuestal"
    SOBRE_PRESUPUESTO = "sobre_presupuesto"
    SALDO_AGOTADO = "saldo_agotado"
    REQUIERE_APROBACION = "requiere_aprobacion"
    FACTURA_SIN_VINCULAR = "factura_sin_vincular"


class TipoVinculacion(enum.Enum):
    """Tipos de vinculación factura-presupuesto."""
    MANUAL = "manual"
    AUTOMATICA = "automatica"
    SUGERIDA = "sugerida"


# ==================== MODELOS ====================

class LineaPresupuesto(Base):
    """
    Línea presupuestal - Planeación del gasto anual.

    Representa una línea de gasto presupuestado para un año fiscal.
    Se carga desde Excel al inicio del año y puede ajustarse con aprobaciones.

    Ejemplo:
    - Código: "TI-001"
    - Nombre: "Historia Clínica - GOMEDISYS"
    - Presupuesto anual: $855,718,668
    - Responsable: KION
    """
    __tablename__ = "lineas_presupuesto"

    # Identificación
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    año = Column(BigInteger, nullable=False, index=True, comment="Año fiscal")
    codigo_linea = Column(String(50), nullable=False, comment="Código único de línea (ej: TI-001)")
    nombre_cuenta = Column(String(500), nullable=False, comment="Nombre descriptivo de la línea")
    descripcion = Column(Text, nullable=True, comment="Descripción detallada")

    # Clasificación
    tipo_linea = Column(
        Enum(TipoLineaPresupuesto),
        nullable=False,
        default=TipoLineaPresupuesto.OPEX,
        comment="Tipo de línea presupuestal"
    )
    area = Column(String(100), nullable=True, index=True, comment="Área responsable")
    centro_costo = Column(String(50), nullable=True, comment="Centro de costo")

    # Responsables
    responsable_id = Column(
        BigInteger,
        ForeignKey("responsables.id", ondelete="SET NULL"),
        nullable=True,
        comment="Responsable principal de la línea"
    )
    responsable_backup_id = Column(
        BigInteger,
        ForeignKey("responsables.id", ondelete="SET NULL"),
        nullable=True,
        comment="Responsable backup"
    )

    # Proveedor esperado
    proveedor_id = Column(
        BigInteger,
        ForeignKey("proveedores.id", ondelete="SET NULL"),
        nullable=True,
        comment="Proveedor principal esperado"
    )

    # Presupuesto mensual (12 columnas para precisión)
    presupuesto_ene = Column(Numeric(15, 2), default=0, nullable=False)
    presupuesto_feb = Column(Numeric(15, 2), default=0, nullable=False)
    presupuesto_mar = Column(Numeric(15, 2), default=0, nullable=False)
    presupuesto_abr = Column(Numeric(15, 2), default=0, nullable=False)
    presupuesto_may = Column(Numeric(15, 2), default=0, nullable=False)
    presupuesto_jun = Column(Numeric(15, 2), default=0, nullable=False)
    presupuesto_jul = Column(Numeric(15, 2), default=0, nullable=False)
    presupuesto_ago = Column(Numeric(15, 2), default=0, nullable=False)
    presupuesto_sep = Column(Numeric(15, 2), default=0, nullable=False)
    presupuesto_oct = Column(Numeric(15, 2), default=0, nullable=False)
    presupuesto_nov = Column(Numeric(15, 2), default=0, nullable=False)
    presupuesto_dic = Column(Numeric(15, 2), default=0, nullable=False)

    # Totales calculados
    presupuesto_anual = Column(
        Numeric(20, 2),
        nullable=False,
        comment="Presupuesto total anual (suma de meses)"
    )
    ejecutado_acumulado = Column(
        Numeric(20, 2),
        default=0,
        nullable=False,
        comment="Total ejecutado hasta la fecha"
    )
    saldo_disponible = Column(
        Numeric(20, 2),
        nullable=False,
        comment="Saldo disponible (presupuesto - ejecutado)"
    )
    porcentaje_ejecucion = Column(
        Numeric(5, 2),
        default=0,
        nullable=False,
        comment="% de ejecución (ejecutado/presupuesto * 100)"
    )

    # Estado y control
    estado = Column(
        Enum(EstadoLineaPresupuesto),
        default=EstadoLineaPresupuesto.BORRADOR,
        nullable=False,
        index=True,
        comment="Estado actual de la línea"
    )
    activo = Column(Boolean, default=True, nullable=False, comment="Línea activa")

    # Aprobaciones
    fecha_aprobacion = Column(DateTime(timezone=True), nullable=True, comment="Cuándo se aprobó")
    aprobado_por = Column(String(100), nullable=True, comment="Quién aprobó")
    observaciones_aprobacion = Column(Text, nullable=True, comment="Observaciones de aprobación")

    # Alertas y umbrales
    umbral_alerta_porcentaje = Column(
        Numeric(5, 2),
        default=90.0,
        nullable=False,
        comment="% de ejecución para generar alerta"
    )
    requiere_aprobacion_sobre_ejecucion = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Requiere aprobación si se excede presupuesto"
    )
    nivel_aprobacion_requerido = Column(
        Enum(NivelAprobacion),
        default=NivelAprobacion.RESPONSABLE_LINEA,
        nullable=False,
        comment="Nivel de aprobación para sobre-ejecuciones"
    )

    # Metadata de importación
    importacion_id = Column(
        BigInteger,
        ForeignKey("importaciones_presupuesto.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID de importación de origen"
    )
    fila_excel_origen = Column(BigInteger, nullable=True, comment="Fila del Excel de origen")

    # Versionamiento
    version = Column(BigInteger, default=1, nullable=False, comment="Versión de la línea")
    version_anterior_id = Column(
        BigInteger,
        ForeignKey("lineas_presupuesto.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID de versión anterior (para histórico)"
    )

    # Timestamps
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    creado_por = Column(String(100), nullable=False, comment="Usuario que creó")
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    actualizado_por = Column(String(100), nullable=True, comment="Último usuario que modificó")

    # Relationships
    responsable = relationship("Responsable", foreign_keys=[responsable_id], lazy="joined")
    responsable_backup = relationship("Responsable", foreign_keys=[responsable_backup_id])
    proveedor = relationship("Proveedor", lazy="joined")
    importacion = relationship("ImportacionPresupuesto", foreign_keys=[importacion_id])
    ejecuciones = relationship("EjecucionPresupuestal", back_populates="linea_presupuesto")

    # Constraints
    __table_args__ = (
        UniqueConstraint('año', 'codigo_linea', name='uix_año_codigo_linea'),
        CheckConstraint('presupuesto_anual >= 0', name='chk_presupuesto_positivo'),
        CheckConstraint('ejecutado_acumulado >= 0', name='chk_ejecutado_positivo'),
        CheckConstraint('porcentaje_ejecucion >= 0 AND porcentaje_ejecucion <= 999', name='chk_porcentaje_rango'),
    )


class EjecucionPresupuestal(Base):
    """
    Ejecución presupuestal - Vinculación de facturas reales con presupuesto.

    Registra la ejecución real del presupuesto al vincular facturas
    con líneas presupuestales. Incluye workflow de aprobación y control
    de desviaciones.

    Ejemplo:
    - Línea: "Historia Clínica - GOMEDISYS"
    - Factura: KION-Ene-821 ($67,794,987)
    - Período: 2025-01
    - Desviación: -3.58% (bajo presupuesto)
    - Estado: Aprobado
    """
    __tablename__ = "ejecuciones_presupuestales"

    # Identificación
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Vinculación
    linea_presupuesto_id = Column(
        BigInteger,
        ForeignKey("lineas_presupuesto.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Línea presupuestal asociada"
    )
    factura_id = Column(
        BigInteger,
        ForeignKey("facturas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Factura real vinculada"
    )

    # Período y temporalidad
    año = Column(BigInteger, nullable=False, index=True, comment="Año de ejecución")
    mes = Column(BigInteger, nullable=False, comment="Mes (1-12)")
    periodo = Column(String(7), nullable=False, index=True, comment="Período YYYY-MM")

    # Valores
    valor_presupuestado = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Valor presupuestado para este período"
    )
    valor_factura = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Valor de la factura vinculada"
    )
    valor_imputado = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Valor imputado a este presupuesto (puede ser parcial)"
    )

    # Análisis de desviación
    desviacion = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Desviación (valor_imputado - valor_presupuestado)"
    )
    desviacion_porcentaje = Column(
        Numeric(8, 4),
        nullable=False,
        comment="Desviación en porcentaje"
    )
    tipo_desviacion = Column(
        Enum(TipoDesviacion),
        nullable=False,
        comment="Clasificación de la desviación"
    )

    # Estado y workflow
    estado = Column(
        Enum(EstadoEjecucion),
        default=EstadoEjecucion.PENDIENTE_VINCULACION,
        nullable=False,
        index=True,
        comment="Estado en el workflow de aprobación"
    )

    # Vinculación automática vs manual
    vinculacion_automatica = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Vinculación automática o manual"
    )
    confianza_vinculacion = Column(
        Numeric(3, 2),
        nullable=True,
        comment="Confianza de vinculación automática (0-1)"
    )
    criterios_matching = Column(
        JSON,
        nullable=True,
        comment="Criterios usados para matching automático"
    )

    # Aprobaciones (multinivel)
    requiere_aprobacion = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Requiere aprobación manual"
    )
    nivel_aprobacion_requerido = Column(
        Enum(NivelAprobacion),
        nullable=True,
        comment="Nivel de aprobación necesario"
    )

    # Aprobador Nivel 1 (Responsable de línea)
    aprobado_nivel1 = Column(Boolean, default=False, comment="Aprobado nivel 1")
    aprobador_nivel1 = Column(String(100), nullable=True, comment="Quién aprobó nivel 1")
    fecha_aprobacion_nivel1 = Column(DateTime(timezone=True), nullable=True)
    observaciones_nivel1 = Column(Text, nullable=True)

    # Aprobador Nivel 2 (Jefe de área)
    aprobado_nivel2 = Column(Boolean, default=False, comment="Aprobado nivel 2")
    aprobador_nivel2 = Column(String(100), nullable=True, comment="Quién aprobó nivel 2")
    fecha_aprobacion_nivel2 = Column(DateTime(timezone=True), nullable=True)
    observaciones_nivel2 = Column(Text, nullable=True)

    # Aprobador Nivel 3 (Gerencia financiera/CFO)
    aprobado_nivel3 = Column(Boolean, default=False, comment="Aprobado nivel 3")
    aprobador_nivel3 = Column(String(100), nullable=True, comment="Quién aprobó nivel 3")
    fecha_aprobacion_nivel3 = Column(DateTime(timezone=True), nullable=True)
    observaciones_nivel3 = Column(Text, nullable=True)

    # Rechazo
    motivo_rechazo = Column(Text, nullable=True, comment="Motivo si fue rechazado")
    rechazado_por = Column(String(100), nullable=True)
    fecha_rechazo = Column(DateTime(timezone=True), nullable=True)

    # Observaciones y justificaciones
    observaciones = Column(Text, nullable=True, comment="Observaciones generales")
    justificacion_desviacion = Column(
        Text,
        nullable=True,
        comment="Justificación de desviación (si aplica)"
    )

    # Alertas generadas
    alerta_generada = Column(Boolean, default=False, comment="Se generó alerta")
    tipo_alerta = Column(String(50), nullable=True, comment="Tipo de alerta generada")
    notificacion_enviada = Column(Boolean, default=False, comment="Se envió notificación")
    destinatarios_notificacion = Column(JSON, nullable=True, comment="Emails notificados")

    # Metadata
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    creado_por = Column(String(100), nullable=False, comment="Usuario que vinculó")
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    actualizado_por = Column(String(100), nullable=True)

    # Relationships
    linea_presupuesto = relationship("LineaPresupuesto", back_populates="ejecuciones")
    factura = relationship("Factura")

    # Constraints
    __table_args__ = (
        UniqueConstraint('linea_presupuesto_id', 'factura_id', name='uix_linea_factura'),
        CheckConstraint('valor_imputado > 0', name='chk_valor_imputado_positivo'),
        CheckConstraint('mes >= 1 AND mes <= 12', name='chk_mes_valido'),
    )
