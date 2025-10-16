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


# ==================== ENUMS ENTERPRISE: CONTROL DE RIESGOS ====================

class TipoServicioProveedor(enum.Enum):
    """
    Clasificación de proveedores según naturaleza del servicio.

    Esta clasificación determina los criterios de aprobación automática:
    - FIJO: Criterios estrictos (95% confianza, sin items nuevos)
    - VARIABLE: Criterios moderados (88% confianza, rango ±30%)
    - POR_CONSUMO: Requiere orden de compra (85% confianza)
    - EVENTUAL: NUNCA auto-aprobar (siempre revisión manual)

    Nivel: Fortune 500 Risk Management
    """
    SERVICIO_FIJO_MENSUAL = "servicio_fijo_mensual"
    # Ejemplos: Arriendo, vigilancia, nómina outsourcing, seguros
    # Características: Monto fijo o muy predecible (CV < 15%)
    # Criterios: CV < 5%, confianza >= 95%, sin items nuevos

    SERVICIO_VARIABLE_PREDECIBLE = "servicio_variable_predecible"
    # Ejemplos: Servicios públicos, telefonía, hosting
    # Características: Varía pero dentro de rango predecible (CV 15-80%)
    # Criterios: CV < 30%, confianza >= 88%, monto en rango ±30%

    SERVICIO_POR_CONSUMO = "servicio_por_consumo"
    # Ejemplos: Materiales, equipos, servicios profesionales
    # Características: Alta variabilidad según necesidad (CV > 80%)
    # Criterios: CV < 50%, confianza >= 85%, requiere orden de compra

    SERVICIO_EVENTUAL = "servicio_eventual"
    # Ejemplos: Proyectos especiales, compras únicas
    # Características: No recurrente
    # Criterios: NUNCA auto-aprobar (siempre revisión manual)


class NivelConfianzaProveedor(enum.Enum):
    """
    Nivel de confianza del proveedor basado en historial y desempeño.

    Determina el umbral de confianza requerido para aprobación automática:
    - NIVEL_1 (Crítico): Servicios críticos, requiere 95%+ confianza
    - NIVEL_2 (Alto): Proveedores establecidos, 92%+ confianza
    - NIVEL_3 (Medio): Proveedores regulares, 88%+ confianza
    - NIVEL_4 (Bajo): Proveedores con incidencias, 95%+ confianza
    - NIVEL_5 (Nuevo): Sin historial, NUNCA auto-aprobar (100%)

    Nivel: Fortune 500 Vendor Management
    """
    NIVEL_1_CRITICO = "nivel_1_critico"
    # Umbral: 95% confianza
    # Proveedores de servicios críticos para operación
    # Antigüedad: 24+ meses sin incidencias

    NIVEL_2_ALTO = "nivel_2_alto"
    # Umbral: 92% confianza
    # Proveedores establecidos con buen historial
    # Antigüedad: 12-24 meses, <2 incidencias/año

    NIVEL_3_MEDIO = "nivel_3_medio"
    # Umbral: 88% confianza
    # Proveedores regulares
    # Antigüedad: 6-12 meses, <3 incidencias/año

    NIVEL_4_BAJO = "nivel_4_bajo"
    # Umbral: 95% confianza (más estricto por historial)
    # Proveedores con incidencias recientes
    # Antigüedad: 3-6 meses O incidencias recientes

    NIVEL_5_NUEVO = "nivel_5_nuevo"
    # Umbral: 100% (NUNCA auto-aprobar)
    # Proveedores nuevos sin historial suficiente
    # Antigüedad: <3 meses


class TipoAlerta(enum.Enum):
    """Tipos de alertas para el sistema de Early Warning."""
    CONFIANZA_BORDE = "confianza_borde"              # 94-95% (cerca del límite)
    VARIACION_PRECIO_MODERADA = "variacion_precio_moderada"  # 10-15% variación
    ITEM_NUEVO_BAJO_VALOR = "item_nuevo_bajo_valor"  # Item nuevo < 10% total
    PATRON_INUSUAL = "patron_inusual"                # Desviación del patrón
    PROVEEDOR_NUEVO = "proveedor_nuevo"              # < 6 meses historial
    MONTO_CERCA_LIMITE = "monto_cerca_limite"        # 90-100% monto máximo
    CAMBIO_FRECUENCIA = "cambio_frecuencia"          # Cambio en frecuencia de facturas


class SeveridadAlerta(enum.Enum):
    """Severidad de alertas para priorización."""
    BAJA = "baja"          # Informativa, revisar en auditoría semanal
    MEDIA = "media"        # Requiere revisión en auditoría diaria
    ALTA = "alta"          # Requiere revisión inmediata
    CRITICA = "critica"    # Bloquea aprobación automática


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

    # ==================== ENTERPRISE: CLASIFICACION Y CONTROL DE RIESGOS ====================
    # Campos agregados por migración 88f9b5fd2ca3

    tipo_servicio_proveedor = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Clasificación del tipo de servicio para ajustar criterios de aprobación"
    )

    nivel_confianza_proveedor = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Nivel de confianza (1-5) basado en antigüedad e historial"
    )

    fecha_inicio_relacion = Column(
        DateTime,
        nullable=True,
        comment="Primera factura registrada del proveedor (para calcular antigüedad)"
    )

    coeficiente_variacion_historico = Column(
        Numeric(7, 2),
        nullable=True,
        comment="CV% de variación de montos históricos"
    )

    requiere_orden_compra_obligatoria = Column(
        Boolean,
        default=False,
        comment="Si TRUE, facturas sin OC no se auto-aprueban (para servicios por consumo)"
    )

    metadata_riesgos = Column(
        JSON,
        nullable=True,
        comment="Metadata de análisis de riesgos: última evaluación, incidentes, etc."
    )

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


class AlertaAprobacionAutomatica(Base):
    """
    Sistema de Alertas Tempranas (Early Warning System) para auditoría continua.

    Registra alertas incluso cuando la factura ES aprobada automáticamente,
    permitiendo auditoría posterior de casos "borderline" o con riesgos moderados.

    Casos de uso:
    - Factura aprobada con confianza 94.5% (cerca del 95%)
    - Factura aprobada con items nuevos de bajo valor
    - Cambios en patrones de proveedores establecidos
    - Montos cerca del límite máximo configurado

    Nivel: Fortune 500 Compliance & Audit
    """
    __tablename__ = "alertas_aprobacion_automatica"

    # Identificación
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    workflow_id = Column(BigInteger, ForeignKey("workflow_aprobacion_facturas.id"), nullable=True, index=True)
    factura_id = Column(BigInteger, ForeignKey("facturas.id"), nullable=False, index=True)

    # Tipo y severidad de alerta
    tipo_alerta = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Tipo de alerta detectada"
    )

    severidad = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Severidad: BAJA (informativa), MEDIA (revisar diario), ALTA (inmediata), CRITICA (bloquea)"
    )

    # Datos de la alerta
    confianza_calculada = Column(Numeric(5, 2), nullable=True, comment="Confianza calculada en la decisión")
    umbral_requerido = Column(Numeric(5, 2), nullable=True, comment="Umbral requerido para aprobación")
    diferencia = Column(Numeric(5, 2), nullable=True, comment="Diferencia entre calculada y requerida")
    valor_detectado = Column(String(255), nullable=True, comment="Valor que generó la alerta")
    valor_esperado = Column(String(255), nullable=True, comment="Valor esperado según patrón")

    # Flags de gestión
    requiere_revision_urgente = Column(
        Boolean,
        nullable=False,
        server_default='0',
        comment="Si TRUE, requiere revisión inmediata por auditor"
    )

    revisada = Column(
        Boolean,
        nullable=False,
        server_default='0',
        index=True,
        comment="Si TRUE, la alerta ya fue revisada por un humano"
    )

    revisada_por = Column(String(255), nullable=True, comment="Usuario que revisó la alerta")
    fecha_revision = Column(DateTime, nullable=True, comment="Cuándo se revisó")
    accion_tomada = Column(Text, nullable=True, comment="Descripción de acción tomada tras revisar")

    # Metadata y auditoría
    metadata_alerta = Column(
        JSON,
        nullable=True,
        comment="Información adicional: contexto, métricas, recomendaciones"
    )

    creado_en = Column(DateTime, nullable=False, server_default=func.now())
    actualizado_en = Column(DateTime, nullable=True, onupdate=func.now())

    # Relaciones
    workflow = relationship("WorkflowAprobacionFactura", foreign_keys=[workflow_id], backref="alertas")
    factura = relationship("Factura", foreign_keys=[factura_id])

    # Índices compuestos para queries frecuentes
    __table_args__ = (
        Index('idx_alertas_pendientes', 'revisada', 'severidad', 'creado_en'),
        Index('idx_alertas_tipo_severidad', 'tipo_alerta', 'severidad'),
        Index('idx_alertas_workflow_factura', 'workflow_id', 'factura_id'),
    )

    def __repr__(self):
        return f"<AlertaAprobacionAutomatica(id={self.id}, tipo={self.tipo_alerta.value}, severidad={self.severidad.value}, revisada={self.revisada})>"


# NOTA: ConfiguracionCorreo fue eliminada (obsoleta, configuración IMAP vieja).
# Ahora usamos CuentaCorreo (app/models/email_config.py) con Microsoft Graph API.
