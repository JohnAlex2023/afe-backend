# app/models/automation_audit.py
"""
Modelo de auditoría para el sistema de automatización.
Registra todas las decisiones automáticas para trazabilidad completa.
"""

from sqlalchemy import Column, BigInteger, String, DateTime, Numeric, JSON, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class AutomationAudit(Base):
    """
    Registro de auditoría para decisiones automáticas.

    Cada vez que el sistema toma una decisión automática sobre una factura,
    se crea un registro aquí con toda la información relevante.
    """
    __tablename__ = "automation_audit"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Relación con la factura
    factura_id = Column(BigInteger, ForeignKey("facturas.id"), nullable=False, index=True)

    # Timestamp de la decisión
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Decisión tomada
    decision = Column(String(50), nullable=False, index=True)
    # Valores posibles: 'aprobada_auto', 'en_revision', 'rechazada'

    # Score de confianza (0.00 - 1.00)
    confianza = Column(Numeric(5, 4), nullable=False)

    # Motivo de la decisión (texto explicativo)
    motivo = Column(Text, nullable=False)

    # Patrón detectado
    patron_detectado = Column(String(50), nullable=True)
    # Valores posibles: 'mensual', 'quincenal', 'semanal', 'bimestral', 'irregular', etc.

    # Factura de referencia usada
    factura_referencia_id = Column(BigInteger, ForeignKey("facturas.id"), nullable=True)

    # Criterios evaluados (JSON con detalles)
    criterios_evaluados = Column(JSON, nullable=True)
    # Estructura: [{"nombre": "patron_recurrencia", "cumplido": true, "peso": 0.35, ...}, ...]

    # Configuración usada en la decisión
    configuracion_utilizada = Column(JSON, nullable=True)
    # Snapshot de la configuración de umbrales al momento de la decisión

    # Metadata adicional
    metadata_decision = Column(JSON, nullable=True)
    # Cualquier información adicional relevante

    # Versión del algoritmo
    version_algoritmo = Column(String(20), nullable=False, server_default="1.0")

    # Información del proveedor al momento de la decisión
    proveedor_nit = Column(String(20), nullable=True, index=True)
    proveedor_nombre = Column(String(500), nullable=True)

    # Monto de la factura (para análisis)
    monto_factura = Column(Numeric(15, 2), nullable=True)

    # ¿Requirió acción manual después?
    requirio_accion_manual = Column(Boolean, default=False, index=True)

    # Si hubo override manual
    override_manual = Column(Boolean, default=False)
    override_por = Column(String(100), nullable=True)
    override_razon = Column(String(1000), nullable=True)
    override_fecha = Column(DateTime(timezone=True), nullable=True)

    # Resultado final (para ML feedback)
    resultado_final = Column(String(50), nullable=True, index=True)
    # 'confirmado', 'revertido', 'modificado'

    # Tiempo de procesamiento (ms)
    tiempo_procesamiento_ms = Column(BigInteger, nullable=True)

    # Relaciones
    factura = relationship("Factura", foreign_keys=[factura_id], backref="audit_logs")
    factura_referencia = relationship("Factura", foreign_keys=[factura_referencia_id])


class AutomationMetrics(Base):
    """
    Métricas agregadas del sistema de automatización.
    Se actualiza periódicamente (cada hora/día) para dashboard.
    """
    __tablename__ = "automation_metrics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Período de la métrica
    periodo = Column(String(20), nullable=False, index=True)
    # Formato: 'YYYY-MM-DD-HH' para métricas horarias, 'YYYY-MM-DD' para diarias

    fecha_calculo = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Contadores básicos
    total_facturas_procesadas = Column(BigInteger, default=0)
    total_aprobadas_automaticamente = Column(BigInteger, default=0)
    total_enviadas_revision = Column(BigInteger, default=0)
    total_rechazadas = Column(BigInteger, default=0)

    # Tasas (porcentajes)
    tasa_automatizacion = Column(Numeric(5, 2), default=0.0)
    # % de facturas aprobadas automáticamente

    tasa_precision = Column(Numeric(5, 2), default=0.0)
    # % de decisiones automáticas que fueron correctas (no requirieron override)

    # Tiempos
    tiempo_promedio_procesamiento_ms = Column(BigInteger, nullable=True)
    tiempo_minimo_procesamiento_ms = Column(BigInteger, nullable=True)
    tiempo_maximo_procesamiento_ms = Column(BigInteger, nullable=True)

    # Confianza promedio
    confianza_promedio = Column(Numeric(5, 4), nullable=True)

    # Patrones detectados
    patrones_detectados = Column(JSON, nullable=True)
    # {"mensual": 15, "quincenal": 3, "irregular": 2}

    # Proveedores procesados
    total_proveedores_procesados = Column(BigInteger, default=0)
    top_proveedores = Column(JSON, nullable=True)
    # Lista de top 10 proveedores por volumen

    # Montos
    monto_total_procesado = Column(Numeric(20, 2), default=0.0)
    monto_total_aprobado_auto = Column(Numeric(20, 2), default=0.0)

    # Errores y excepciones
    total_errores = Column(BigInteger, default=0)
    errores_detalle = Column(JSON, nullable=True)

    # Metadata adicional
    metadata_info = Column(JSON, nullable=True)


class ConfiguracionAutomatizacion(Base):
    """
    Configuración persistente del sistema de automatización.
    Permite modificar parámetros sin modificar código.
    """
    __tablename__ = "configuracion_automatizacion"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Clave de configuración (única)
    clave = Column(String(100), nullable=False, unique=True, index=True)

    # Valor (JSON para flexibilidad)
    valor = Column(JSON, nullable=False)

    # Tipo de dato
    tipo_dato = Column(String(50), nullable=False)
    # 'float', 'int', 'bool', 'string', 'json'

    # Descripción
    descripcion = Column(Text, nullable=True)

    # Validación
    valor_minimo = Column(JSON, nullable=True)
    valor_maximo = Column(JSON, nullable=True)
    valores_permitidos = Column(JSON, nullable=True)

    # Metadata
    categoria = Column(String(100), nullable=True, index=True)
    # 'decision_engine', 'pattern_detector', 'notification', etc.

    activa = Column(Boolean, default=True)

    # Auditoría
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())
    actualizado_por = Column(String(100), nullable=True)

    # Versión (para cambios)
    version = Column(BigInteger, default=1)


class ProveedorTrust(Base):
    """
    Nivel de confianza por proveedor para decisiones automáticas.
    Se actualiza dinámicamente basándose en el historial.
    """
    __tablename__ = "proveedor_trust"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Proveedor
    proveedor_id = Column(BigInteger, ForeignKey("proveedores.id"), nullable=False, unique=True, index=True)

    # Score de confianza (0.00 - 1.00)
    trust_score = Column(Numeric(5, 4), nullable=False, default=0.5)

    # Nivel de confianza (categoría)
    nivel_confianza = Column(String(20), nullable=False, default='medio')
    # 'alto' (>0.85), 'medio' (0.50-0.85), 'bajo' (<0.50), 'bloqueado'

    # Estadísticas
    total_facturas = Column(BigInteger, default=0)
    facturas_aprobadas = Column(BigInteger, default=0)
    facturas_rechazadas = Column(BigInteger, default=0)
    facturas_aprobadas_auto = Column(BigInteger, default=0)

    # Tasas
    tasa_aprobacion = Column(Numeric(5, 2), default=0.0)
    tasa_automatizacion_exitosa = Column(Numeric(5, 2), default=0.0)

    # Historial de confianza (últimos 12 meses)
    historial_confianza = Column(JSON, nullable=True)
    # [{"periodo": "2025-01", "score": 0.85}, ...]

    # Patrones identificados
    patrones_recurrentes = Column(JSON, nullable=True)
    # {"mensual_servicio_cloud": {"frecuencia": "mensual", "monto_promedio": 5000000}}

    # Flags especiales
    bloqueado = Column(Boolean, default=False)
    motivo_bloqueo = Column(Text, nullable=True)
    bloqueado_por = Column(String(100), nullable=True)
    bloqueado_en = Column(DateTime(timezone=True), nullable=True)

    requiere_revision_siempre = Column(Boolean, default=False)

    # Auditoría
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())

    # Relación
    proveedor = relationship("Proveedor", backref="trust_info")
