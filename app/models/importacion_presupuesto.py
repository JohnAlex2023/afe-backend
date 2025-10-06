"""
Modelo de base de datos para auditoría de importaciones presupuestales.

Nivel: Enterprise
"""

from sqlalchemy import Column, BigInteger, String, DateTime, Numeric, Text, Enum, JSON, Boolean
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class EstadoImportacion(enum.Enum):
    """Estados del proceso de importación."""
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    COMPLETADO = "completado"
    ERROR = "error"


class ImportacionPresupuesto(Base):
    """
    Tabla de auditoría para importaciones de presupuesto.

    Registra cada importación de archivo Excel/CSV para comparación
    presupuestal, incluyendo resultados y métricas.
    """
    __tablename__ = "importaciones_presupuesto"

    # Identificación
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    archivo_nombre = Column(String(500), nullable=False, comment="Nombre del archivo original")
    archivo_hash = Column(String(64), nullable=True, comment="Hash SHA256 del archivo")
    archivo_tamaño = Column(BigInteger, nullable=True, comment="Tamaño del archivo en bytes")

    # Período y contexto
    año = Column(BigInteger, nullable=False, index=True, comment="Año del presupuesto")
    mes_inicio = Column(BigInteger, nullable=True, comment="Mes de inicio (1-12)")
    mes_fin = Column(BigInteger, nullable=True, comment="Mes de fin (1-12)")

    # Estado y proceso
    estado = Column(
        Enum(EstadoImportacion),
        default=EstadoImportacion.PENDIENTE,
        nullable=False,
        index=True,
        comment="Estado de la importación"
    )
    fecha_inicio = Column(DateTime(timezone=True), server_default=func.now(), comment="Cuándo inició")
    fecha_fin = Column(DateTime(timezone=True), nullable=True, comment="Cuándo terminó")
    tiempo_procesamiento_segundos = Column(Numeric(10, 2), nullable=True, comment="Tiempo de procesamiento")

    # Usuario y auditoría
    usuario_importador = Column(String(100), nullable=False, comment="Usuario que realizó la importación")
    descripcion = Column(String(1000), nullable=True, comment="Descripción de la importación")

    # Resultados numéricos
    total_lineas_presupuesto = Column(BigInteger, default=0, comment="Total líneas presupuestales procesadas")
    total_facturas_comparadas = Column(BigInteger, default=0, comment="Total facturas comparadas")
    total_facturas_encontradas = Column(BigInteger, default=0, comment="Facturas encontradas en BD")
    total_facturas_faltantes = Column(BigInteger, default=0, comment="Facturas faltantes")
    total_desviaciones = Column(BigInteger, default=0, comment="Desviaciones detectadas")

    # Resultados financieros
    presupuesto_total = Column(Numeric(20, 2), default=0, comment="Presupuesto total del archivo")
    ejecucion_total = Column(Numeric(20, 2), default=0, comment="Ejecución total")
    desviacion_global = Column(Numeric(20, 2), default=0, comment="Desviación global")
    porcentaje_ejecucion = Column(Numeric(5, 2), default=0, comment="% de ejecución global")

    # Datos completos (JSON)
    reporte_completo = Column(JSON, nullable=True, comment="Reporte completo en formato JSON")
    errores = Column(JSON, nullable=True, comment="Lista de errores encontrados")
    advertencias = Column(JSON, nullable=True, comment="Lista de advertencias")

    # Archivos generados
    pdf_generado = Column(Boolean, default=False, comment="Se generó PDF del reporte")
    pdf_ruta = Column(String(500), nullable=True, comment="Ruta del PDF generado")
    excel_resultado_ruta = Column(String(500), nullable=True, comment="Ruta del Excel con resultados")

    # Email
    email_enviado = Column(Boolean, default=False, comment="Se envió email con reporte")
    email_destino = Column(String(500), nullable=True, comment="Email(s) destino separados por coma")
    email_fecha_envio = Column(DateTime(timezone=True), nullable=True, comment="Cuándo se envió el email")

    # Metadata adicional
    config_importacion = Column(JSON, nullable=True, comment="Configuración usada para la importación")
    notas = Column(Text, nullable=True, comment="Notas adicionales")

    # Timestamps
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
