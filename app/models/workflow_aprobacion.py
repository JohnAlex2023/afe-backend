"""
Modelos de datos para workflow de aprobación automática de facturas.

Sistema de automatización inteligente que:
- Lee correos automáticamente
- Identifica NIT y asigna responsable
- Aprueba automáticamente facturas idénticas al mes anterior
- Gestiona flujo de aprobación manual
- Genera notificaciones y trazabilidad completa

Nivel: Enterprise Automation
"""

from sqlalchemy import (
    Column, BigInteger, String, DateTime, Numeric, Text,
    Enum, JSON, Boolean, ForeignKey, Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum
from datetime import datetime


# ==================== ENUMS ====================

class EstadoFacturaWorkflow(enum.Enum):
    """Estados del workflow de aprobación de facturas."""
    RECIBIDA = "recibida"  # Factura recibida por correo
    EN_ANALISIS = "en_analisis"  # Analizando si es idéntica
    APROBADA_AUTO = "aprobada_auto"  # Aprobada automáticamente
    PENDIENTE_REVISION = "pendiente_revision"  # Requiere revisión manual
    EN_REVISION = "en_revision"  # Responsable está revisando
    APROBADA_MANUAL = "aprobada_manual"  # Aprobada manualmente
    RECHAZADA = "rechazada"  # Rechazada
    OBSERVADA = "observada"  # Tiene observaciones
    ENVIADA_CONTABILIDAD = "enviada_contabilidad"  # Enviada a contabilidad
    PROCESADA = "procesada"  # Procesada completamente


class TipoAprobacion(enum.Enum):
    """Tipo de aprobación realizada."""
    AUTOMATICA = "automatica"  # Idéntica al mes anterior
    MANUAL = "manual"  # Revisada y aprobada por responsable
    MASIVA = "masiva"  # Aprobación en lote
    FORZADA = "forzada"  # Aprobación administrativa


class MotivoRechazo(enum.Enum):
    """Motivos de rechazo de factura."""
    MONTO_INCORRECTO = "monto_incorrecto"
    SERVICIO_NO_PRESTADO = "servicio_no_prestado"
    PROVEEDOR_INCORRECTO = "proveedor_incorrecto"
    DUPLICADA = "duplicada"
    SIN_PRESUPUESTO = "sin_presupuesto"
    OTRO = "otro"


class TipoNotificacion(enum.Enum):
    """Tipos de notificación del sistema."""
    FACTURA_RECIBIDA = "factura_recibida"
    PENDIENTE_REVISION = "pendiente_revision"
    FACTURA_APROBADA = "factura_aprobada"
    FACTURA_RECHAZADA = "factura_rechazada"
    RECORDATORIO = "recordatorio"
    ALERTA = "alerta"


# ==================== MODELOS ====================

class WorkflowAprobacionFactura(Base):
    """
    Workflow de aprobación automática/manual de facturas.

    Registra todo el ciclo de vida de una factura desde que se recibe
    por correo hasta que se envía a contabilidad.
    """
    __tablename__ = "workflow_aprobacion_facturas"

    # Identificación
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    factura_id = Column(BigInteger, ForeignKey("facturas.id"), nullable=False, index=True)

    # Información del correo
    email_id = Column(String(255), nullable=True, comment="ID del correo en el servidor")
    email_asunto = Column(String(500), nullable=True, comment="Asunto del correo")
    email_remitente = Column(String(255), nullable=True, comment="Email del remitente")
    email_fecha_recepcion = Column(DateTime, nullable=True, comment="Fecha de recepción del correo")
    email_body_preview = Column(Text, nullable=True, comment="Preview del cuerpo del correo")

    # Estado del workflow
    estado = Column(
        Enum(EstadoFacturaWorkflow),
        nullable=False,
        default=EstadoFacturaWorkflow.RECIBIDA,
        index=True,
        comment="Estado actual en el workflow"
    )
    estado_anterior = Column(
        Enum(EstadoFacturaWorkflow),
        nullable=True,
        comment="Estado previo (para trazabilidad)"
    )
    fecha_cambio_estado = Column(DateTime, default=datetime.now, comment="Última vez que cambió de estado")

    # Asignación automática
    nit_proveedor = Column(String(20), nullable=True, index=True, comment="NIT identificado automáticamente")
    responsable_id = Column(BigInteger, ForeignKey("responsables.id"), nullable=True, index=True)
    area_responsable = Column(String(100), nullable=True, comment="Área del responsable")
    fecha_asignacion = Column(DateTime, nullable=True, comment="Cuándo se asignó al responsable")

    # Análisis de identidad (comparación con mes anterior)
    factura_mes_anterior_id = Column(BigInteger, ForeignKey("facturas.id"), nullable=True, comment="ID factura del mes anterior")
    es_identica_mes_anterior = Column(Boolean, default=False, comment="¿Es idéntica a la del mes anterior?")
    porcentaje_similitud = Column(Numeric(5, 2), nullable=True, comment="% de similitud (0-100)")
    diferencias_detectadas = Column(JSON, nullable=True, comment="Lista de diferencias encontradas")

    # Criterios de comparación
    criterios_comparacion = Column(JSON, nullable=True, comment="""
    {
        'monto_igual': true/false,
        'proveedor_igual': true/false,
        'concepto_igual': true/false,
        'fecha_similar': true/false
    }
    """)

    # Aprobación
    tipo_aprobacion = Column(Enum(TipoAprobacion), nullable=True, comment="Tipo de aprobación realizada")
    aprobada = Column(Boolean, default=False, comment="¿Fue aprobada?")
    aprobada_por = Column(String(255), nullable=True, comment="Usuario que aprobó")
    fecha_aprobacion = Column(DateTime, nullable=True, comment="Fecha de aprobación")
    observaciones_aprobacion = Column(Text, nullable=True, comment="Observaciones del aprobador")

    # Rechazo
    rechazada = Column(Boolean, default=False, comment="¿Fue rechazada?")
    rechazada_por = Column(String(255), nullable=True, comment="Usuario que rechazó")
    fecha_rechazo = Column(DateTime, nullable=True, comment="Fecha de rechazo")
    motivo_rechazo = Column(Enum(MotivoRechazo), nullable=True)
    detalle_rechazo = Column(Text, nullable=True, comment="Detalle del rechazo")

    # Tiempo de procesamiento
    tiempo_en_analisis = Column(BigInteger, nullable=True, comment="Segundos en análisis")
    tiempo_en_revision = Column(BigInteger, nullable=True, comment="Segundos en revisión")
    tiempo_total_aprobacion = Column(BigInteger, nullable=True, comment="Segundos totales hasta aprobación")

    # Notificaciones enviadas
    notificaciones_enviadas = Column(JSON, nullable=True, comment="""
    [
        {'tipo': 'factura_recibida', 'fecha': '...', 'destinatarios': [...]}
    ]
    """)
    recordatorios_enviados = Column(BigInteger, default=0, comment="Cantidad de recordatorios enviados")

    # Metadata
    metadata_workflow = Column(JSON, nullable=True, comment="Información adicional del workflow")

    # Auditoría
    creado_en = Column(DateTime, default=datetime.now, nullable=False)
    actualizado_en = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    creado_por = Column(String(255), nullable=True, default="SISTEMA_AUTO")
    actualizado_por = Column(String(255), nullable=True)

    # Relaciones
    factura = relationship("Factura", foreign_keys=[factura_id])
    factura_anterior = relationship("Factura", foreign_keys=[factura_mes_anterior_id])
    responsable = relationship("Responsable", foreign_keys=[responsable_id])

    # Índices compuestos para consultas frecuentes
    __table_args__ = (
        Index('idx_workflow_estado_responsable', 'estado', 'responsable_id'),
        Index('idx_workflow_nit_fecha', 'nit_proveedor', 'email_fecha_recepcion'),
        Index('idx_workflow_estado_fecha', 'estado', 'fecha_cambio_estado'),
    )


class AsignacionNitResponsable(Base):
    """
    Tabla de configuración: NIT → Responsable.

    Define qué responsable debe aprobar las facturas de cada proveedor.
    """
    __tablename__ = "asignacion_nit_responsable"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nit = Column(String(20), nullable=False, unique=True, index=True, comment="NIT del proveedor")
    nombre_proveedor = Column(String(255), nullable=True, comment="Nombre comercial del proveedor")

    responsable_id = Column(BigInteger, ForeignKey("responsables.id"), nullable=False, index=True)
    area = Column(String(100), nullable=True, comment="Área responsable (TI, Operaciones, etc.)")

    # Configuración de aprobación automática
    permitir_aprobacion_automatica = Column(Boolean, default=True, comment="¿Permitir aprobación automática?")
    requiere_revision_siempre = Column(Boolean, default=False, comment="¿Siempre requiere revisión manual?")

    # Umbrales
    monto_maximo_auto_aprobacion = Column(Numeric(15, 2), nullable=True, comment="Monto máximo para auto-aprobar")
    porcentaje_variacion_permitido = Column(Numeric(5, 2), default=5.0, comment="% variación permitida para auto-aprobar")

    # Notificaciones
    emails_notificacion = Column(JSON, nullable=True, comment="Emails adicionales a notificar")

    # Activo/Inactivo
    activo = Column(Boolean, default=True, index=True)

    # Auditoría
    creado_en = Column(DateTime, default=datetime.now)
    actualizado_en = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    creado_por = Column(String(255), nullable=True)
    actualizado_por = Column(String(255), nullable=True)

    # Relaciones
    responsable = relationship("Responsable", foreign_keys=[responsable_id])


class NotificacionWorkflow(Base):
    """
    Registro de notificaciones enviadas en el workflow.
    """
    __tablename__ = "notificaciones_workflow"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    workflow_id = Column(BigInteger, ForeignKey("workflow_aprobacion_facturas.id"), nullable=False, index=True)

    tipo = Column(Enum(TipoNotificacion), nullable=False, index=True)
    destinatarios = Column(JSON, nullable=False, comment="Lista de emails destinatarios")
    asunto = Column(String(500), nullable=True)
    cuerpo = Column(Text, nullable=True)

    enviada = Column(Boolean, default=False, index=True)
    fecha_envio = Column(DateTime, nullable=True)
    proveedor_email = Column(String(100), nullable=True, comment="Gmail, Outlook, SendGrid, etc.")

    # Respuestas/Clicks
    abierta = Column(Boolean, default=False)
    fecha_apertura = Column(DateTime, nullable=True)
    respondida = Column(Boolean, default=False)
    fecha_respuesta = Column(DateTime, nullable=True)

    # Errores
    error = Column(Text, nullable=True)
    intentos_envio = Column(BigInteger, default=0)

    # Auditoría
    creado_en = Column(DateTime, default=datetime.now)

    # Relaciones
    workflow = relationship("WorkflowAprobacionFactura", foreign_keys=[workflow_id])

    # Índice
    __table_args__ = (
        Index('idx_notif_workflow_tipo', 'workflow_id', 'tipo'),
    )


# NOTA: ConfiguracionCorreo fue eliminada (obsoleta, configuración IMAP vieja).
# Ahora usamos CuentaCorreo (app/models/email_config.py) con Microsoft Graph API.
