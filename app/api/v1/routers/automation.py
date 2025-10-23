# app/api/v1/routers/automation.py
"""
Router para las APIs del sistema de automatización de facturas.

Proporciona endpoints para:
- Ejecutar procesamiento manual de automatización
- Consultar estado de facturas procesadas automáticamente  
- Configurar parámetros de automatización
- Obtener estadísticas del sistema
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.automation.automation_service import AutomationService
from app.services.automation.notification_service import NotificationService, ConfiguracionNotificacion
from app.services.audit_service import AuditService
from app.crud import factura as crud_factura
from app.models.factura import Factura, EstadoFactura
from app.schemas.common import ResponseBase
from pydantic import BaseModel, Field


router = APIRouter(tags=["Automatización"])


# ==================== ENDPOINT DE INICIALIZACIÓN ENTERPRISE ====================

@router.post("/inicializar-sistema", summary=" Inicialización Enterprise del Sistema Completo")
def inicializar_sistema_completo(
    archivo_presupuesto: Optional[str] = None,
    año_fiscal: int = 2025,
    responsable_default_id: int = 1,
    ejecutar_vinculacion: bool = True,
    ejecutar_workflow: bool = True,
    dry_run: bool = False,
    db: Session = Depends(get_db)
):
    """
    **INICIALIZACIÓN COMPLETA DEL SISTEMA ENTERPRISE**

    Ejecuta la inicialización orquestada de todo el sistema:

    1.   **Verificación de Estado**: Analiza el estado actual
    2.   **Validación de Pre-requisitos**: Valida datos y configuraciones
    3.   **Importación de Presupuesto**: Importa desde Excel (si se proporciona)
    4.   **Auto-configuración NIT-Responsable**: Crea asignaciones automáticamente
    5.   **Vinculación de Facturas**: Vincula facturas existentes con presupuesto
    6.   **Activación de Workflow**: Activa workflow de aprobación
    7.   **Reporte Ejecutivo**: Genera reporte completo

    **Características Enterprise:**
    - Transacciones atómicas (todo o nada)
    - Rollback automático en errores
    - Idempotente (se puede ejecutar múltiples veces)
    - Logging detallado
    - Dry-run para simulación

    **Parámetros:**
    - `archivo_presupuesto`: Ruta al Excel de presupuesto (opcional)
    - `año_fiscal`: Año a procesar (default: 2025)
    - `responsable_default_id`: ID del responsable por defecto
    - `ejecutar_vinculacion`: Si debe vincular facturas (default: true)
    - `ejecutar_workflow`: Si debe activar workflow (default: true)
    - `dry_run`: Si true, solo simula sin hacer cambios (default: false)

    **Ejemplo de uso:**
    ```bash
    # Simular (dry-run)
    POST /api/v1/automation/inicializar-sistema?dry_run=true

    # Ejecutar completo
    POST /api/v1/automation/inicializar-sistema?archivo_presupuesto=presupuesto.xlsx
    ```
    """
    from app.services.inicializacion_sistema import InicializacionSistemaService

    servicio = InicializacionSistemaService(db)

    resultado = servicio.inicializar_sistema_completo(
        archivo_presupuesto=archivo_presupuesto,
        año_fiscal=año_fiscal,
        responsable_default_id=responsable_default_id,
        ejecutar_vinculacion=ejecutar_vinculacion,
        ejecutar_workflow=ejecutar_workflow,
        dry_run=dry_run
    )

    if not resultado.get("exito"):
        raise HTTPException(
            status_code=500,
            detail={
                "mensaje": "Error en la inicialización del sistema",
                "errores": resultado.get("errores", [])
            }
        )

    return resultado


# Esquemas de respuesta
class EstadisticasAutomatizacion(BaseModel):
    """Esquema para estadísticas de automatización."""
    facturas_procesadas_hoy: int
    facturas_aprobadas_automaticamente: int
    facturas_en_revision: int
    tasa_automatizacion: float
    tiempo_promedio_procesamiento: Optional[float]
    ultimo_procesamiento: Optional[datetime]


class ConfiguracionAutomatizacion(BaseModel):
    """Esquema para configuración de automatización."""
    confianza_minima_aprobacion: float = Field(ge=0.0, le=1.0, default=0.85)
    dias_historico_patron: int = Field(ge=7, le=365, default=90)
    variacion_monto_permitida: float = Field(ge=0.0, le=1.0, default=0.10)
    requiere_orden_compra: bool = False
    notificaciones_activas: bool = True
    procesamiento_automatico_activo: bool = True


class SolicitudProcesamiento(BaseModel):
    """Esquema para solicitud de procesamiento manual."""
    limite_facturas: int = Field(ge=1, le=100, default=20)
    modo_debug: bool = False
    solo_proveedor_id: Optional[int] = None
    forzar_reprocesamiento: bool = False


class ResultadoFacturaAutomatizada(BaseModel):
    """Esquema para resultado de factura procesada."""
    factura_id: int
    numero_factura: str
    decision: str
    confianza: float
    motivo: str
    fecha_procesamiento: datetime
    requiere_accion_manual: bool


# Instancias de servicios (se crean al cargar el módulo)
automation_service = AutomationService()
notification_service = NotificationService()


@router.post("/procesar", response_model=Dict[str, Any])
async def procesar_facturas_pendientes(
    solicitud: SolicitudProcesamiento,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Ejecuta el procesamiento automático de facturas pendientes.
    
    Esta operación puede tomar varios minutos dependiendo de la cantidad
    de facturas pendientes.
    """
    try:
        # Validar que hay facturas pendientes
        facturas_pendientes = crud_factura.get_facturas_pendientes_procesamiento(
            db, limit=solicitud.limite_facturas
        )
        
        if not facturas_pendientes:
            return ResponseBase(
                success=True,
                message="No hay facturas pendientes de procesamiento automático",
                data={"facturas_procesadas": 0}
            )
        
        # Filtrar por proveedor si se especifica
        if solicitud.solo_proveedor_id:
            facturas_pendientes = [
                f for f in facturas_pendientes 
                if f.proveedor_id == solicitud.solo_proveedor_id
            ]
        
        # Ejecutar procesamiento
        resultado = automation_service.procesar_facturas_pendientes(
            db=db,
            limite_facturas=len(facturas_pendientes),
            modo_debug=solicitud.modo_debug
        )
        
        # Programar envío de notificaciones en segundo plano
        if resultado['resumen_general']['facturas_procesadas'] > 0:
            background_tasks.add_task(
                enviar_notificaciones_procesamiento,
                db,
                resultado
            )
        
        return ResponseBase(
            success=True,
            message=f"Procesadas {resultado['resumen_general']['facturas_procesadas']} facturas",
            data=resultado
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en el procesamiento automático: {str(e)}"
        )


@router.get("/estadisticas", response_model=EstadisticasAutomatizacion)
async def obtener_estadisticas_automatizacion(
    dias_atras: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas del sistema de automatización.
    """
    try:
        fecha_inicio = datetime.utcnow() - timedelta(days=dias_atras)
        
        # Consultar facturas procesadas automáticamente
        facturas_automatizadas = crud_factura.get_facturas_procesadas_automaticamente(
            db, fecha_desde=fecha_inicio
        )
        
        # Calcular estadísticas
        total_procesadas = len(facturas_automatizadas)
        aprobadas_auto = len([
            f for f in facturas_automatizadas 
            if f.estado == EstadoFactura.aprobada_auto
        ])
        en_revision = len([
            f for f in facturas_automatizadas 
            if f.estado == EstadoFactura.en_revision
        ])
        
        tasa_automatizacion = (aprobadas_auto / max(total_procesadas, 1)) * 100
        
        # Obtener último procesamiento
        ultimo_procesamiento = None
        if facturas_automatizadas:
            ultima_factura = max(
                facturas_automatizadas, 
                key=lambda x: x.fecha_procesamiento_auto or datetime.min
            )
            ultimo_procesamiento = ultima_factura.fecha_procesamiento_auto
        
        return EstadisticasAutomatizacion(
            facturas_procesadas_hoy=total_procesadas,
            facturas_aprobadas_automaticamente=aprobadas_auto,
            facturas_en_revision=en_revision,
            tasa_automatizacion=tasa_automatizacion,
            tiempo_promedio_procesamiento=None,  # Por implementar
            ultimo_procesamiento=ultimo_procesamiento
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@router.get("/facturas-procesadas", response_model=List[ResultadoFacturaAutomatizada])
async def obtener_facturas_procesadas(
    dias_atras: int = Query(default=7, ge=1, le=90),
    estado: Optional[str] = Query(default=None),
    proveedor_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de facturas procesadas automáticamente.
    """
    try:
        fecha_inicio = datetime.utcnow() - timedelta(days=dias_atras)
        
        # Obtener facturas procesadas
        facturas = crud_factura.get_facturas_procesadas_automaticamente(
            db, 
            fecha_desde=fecha_inicio,
            estado=estado,
            proveedor_id=proveedor_id,
            limit=limit
        )
        
        # Convertir a esquema de respuesta
        resultados = []
        for factura in facturas:
            resultado = ResultadoFacturaAutomatizada(
                factura_id=factura.id,
                numero_factura=factura.numero_factura,
                decision=factura.estado.value if factura.estado else "desconocido",
                confianza=float(factura.confianza_automatica or 0),
                motivo=factura.motivo_decision or "",
                fecha_procesamiento=factura.fecha_procesamiento_auto or datetime.utcnow(),
                requiere_accion_manual=(factura.estado != EstadoFactura.aprobada_auto)
            )
            resultados.append(resultado)
        
        return resultados
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo facturas procesadas: {str(e)}"
        )


@router.get("/configuracion", response_model=Dict[str, Any])
async def obtener_configuracion():
    """
    Obtiene la configuración actual del sistema de automatización.
    """
    try:
        config = automation_service.obtener_configuracion_actual()
        return ResponseBase(
            success=True,
            message="Configuración obtenida exitosamente",
            data=config
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo configuración: {str(e)}"
        )


@router.put("/configuracion")
async def actualizar_configuracion(
    nueva_config: ConfiguracionAutomatizacion,
    db: Session = Depends(get_db)
):
    """
    Actualiza la configuración del sistema de automatización.
    """
    try:
        # Convertir a formato interno
        config_interna = {
            'decision_engine': {
                'confianza_minima_aprobacion': nueva_config.confianza_minima_aprobacion,
                'requiere_orden_compra': nueva_config.requiere_orden_compra
            },
            'pattern_detector': {
                'dias_historico': nueva_config.dias_historico_patron,
                'tolerancia_variacion_monto': nueva_config.variacion_monto_permitida
            }
        }
        
        # Aplicar configuración
        automation_service.actualizar_configuracion(config_interna)
        
        # Registrar cambio en auditoría
        from app.crud import audit as crud_audit
        crud_audit.create_audit(
            db=db,
            entidad="configuracion_automatizacion",
            entidad_id=0,
            accion="actualizacion",
            usuario="sistema",
            detalle=nueva_config.dict()
        )
        
        return ResponseBase(
            success=True,
            message="Configuración actualizada exitosamente",
            data=nueva_config.dict()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando configuración: {str(e)}"
        )


@router.post("/reprocesar/{factura_id}")
async def reprocesar_factura(
    factura_id: int,
    modo_debug: bool = Query(default=False),
    db: Session = Depends(get_db)
):
    """
    Reprocesa una factura específica con el sistema de automatización.
    """
    try:
        # Obtener la factura
        factura = crud_factura.get_factura(db, factura_id)
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        # Resetear campos de procesamiento automático
        campos_reset = {
            'patron_recurrencia': None,
            'confianza_automatica': None,
            'factura_referencia_id': None,
            'motivo_decision': None,
            'procesamiento_info': None,
            'fecha_procesamiento_auto': None,
            'aprobada_automaticamente': False
        }
        crud_factura.update_factura(db, factura, campos_reset)
        
        # Reprocesar
        resultado = automation_service.procesar_factura_individual(
            db, factura, modo_debug
        )
        
        return ResponseBase(
            success=True,
            message=f"Factura {factura.numero_factura} reprocesada exitosamente",
            data=resultado
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reprocesando factura: {str(e)}"
        )


@router.get("/patrones/{proveedor_id}")
async def analizar_patrones_proveedor(
    proveedor_id: int,
    dias_atras: int = Query(default=90, ge=30, le=365),
    db: Session = Depends(get_db)
):
    """
    Analiza los patrones de facturación de un proveedor específico.
    """
    try:
        # Obtener facturas del proveedor
        fecha_inicio = datetime.utcnow() - timedelta(days=dias_atras)
        facturas = crud_factura.get_facturas_by_proveedor_fecha(
            db, proveedor_id, fecha_inicio
        )
        
        if not facturas:
            return ResponseBase(
                success=True,
                message="No se encontraron facturas para análisis",
                data={"patrones": [], "total_facturas": 0}
            )
        
        # Agrupar por concepto normalizado y analizar patrones
        patrones_detectados = {}
        
        for factura in facturas:
            concepto = factura.concepto_normalizado or "sin_concepto"
            if concepto not in patrones_detectados:
                patrones_detectados[concepto] = []
            patrones_detectados[concepto].append(factura)
        
        # Analizar cada grupo de facturas
        analisis_patrones = []
        pattern_detector = automation_service.pattern_detector
        
        for concepto, grupo_facturas in patrones_detectados.items():
            if len(grupo_facturas) >= 2:  # Mínimo 2 facturas para detectar patrón
                # Tomar la última factura como referencia
                factura_referencia = max(grupo_facturas, key=lambda x: x.fecha_emision)
                facturas_historicas = [f for f in grupo_facturas if f.id != factura_referencia.id]
                
                resultado_patron = pattern_detector.analizar_patron_recurrencia(
                    factura_referencia, facturas_historicas
                )
                
                analisis_patrones.append({
                    'concepto': concepto,
                    'total_facturas': len(grupo_facturas),
                    'es_recurrente': resultado_patron.es_recurrente,
                    'patron_temporal': resultado_patron.patron_temporal.tipo,
                    'confianza_patron': float(resultado_patron.confianza_global),
                    'promedio_dias': resultado_patron.patron_temporal.promedio_dias,
                    'monto_estable': resultado_patron.patron_monto.estable,
                    'variacion_monto_pct': float(resultado_patron.patron_monto.variacion_porcentaje)
                })
        
        return ResponseBase(
            success=True,
            message=f"Análisis completado para {len(facturas)} facturas",
            data={
                "patrones": analisis_patrones,
                "total_facturas": len(facturas),
                "conceptos_analizados": len(patrones_detectados)
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analizando patrones del proveedor: {str(e)}"
        )


@router.post("/notificar-resumen")
async def enviar_notificacion_resumen_manual(
    dias_atras: int = Query(default=1, ge=1, le=7),
    responsables_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db)
):
    """
    Envía manualmente un resumen de procesamiento a los responsables.
    """
    try:
        # Obtener estadísticas del período
        fecha_inicio = datetime.utcnow() - timedelta(days=dias_atras)
        facturas_procesadas = crud_factura.get_facturas_procesadas_automaticamente(
            db, fecha_desde=fecha_inicio
        )
        
        # Simular estadísticas de procesamiento
        estadisticas = {
            'resumen_general': {
                'facturas_procesadas': len(facturas_procesadas),
                'aprobadas_automaticamente': len([f for f in facturas_procesadas if f.estado == EstadoFactura.aprobada_auto]),
                'enviadas_revision': len([f for f in facturas_procesadas if f.estado == EstadoFactura.en_revision]),
                'tasa_automatizacion': 0
            }
        }
        
        # Calcular tasa
        if estadisticas['resumen_general']['facturas_procesadas'] > 0:
            estadisticas['resumen_general']['tasa_automatizacion'] = (
                estadisticas['resumen_general']['aprobadas_automaticamente'] / 
                estadisticas['resumen_general']['facturas_procesadas'] * 100
            )
        
        # Obtener facturas pendientes
        facturas_pendientes = crud_factura.get_facturas_pendientes_procesamiento(db)
        
        # Enviar notificación
        resultado = notification_service.enviar_resumen_procesamiento(
            db=db,
            estadisticas_procesamiento=estadisticas,
            facturas_pendientes=facturas_pendientes,
            responsables_notificar=responsables_ids
        )
        
        return ResponseBase(
            success=resultado['exito'],
            message="Notificación de resumen enviada" if resultado['exito'] else "Error enviando notificación",
            data=resultado
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error enviando notificación de resumen: {str(e)}"
        )


@router.get("/dashboard/metricas", summary="Métricas del Dashboard en Tiempo Real")
async def obtener_metricas_dashboard(
    db: Session = Depends(get_db)
):
    """
    **ENDPOINT OPTIMIZADO PARA DASHBOARD**

    Retorna métricas en tiempo real para el dashboard principal:
    - Facturas aprobadas automáticamente hoy
    - Facturas en revisión manual
    - Facturas pendientes de procesamiento
    - Tasa de automatización del día
    - Últimas facturas procesadas
    - Estadísticas de la última ejecución

    **Optimizado para:**
    - Respuesta rápida (< 500ms)
    - Datos agregados y cacheables
    - Formato listo para visualización
    """
    try:
        from sqlalchemy import and_, func
        from datetime import date

        hoy = datetime.utcnow().date()

        # Métricas del día actual
        facturas_aprobadas_hoy = db.query(func.count(Factura.id)).filter(
            and_(
                Factura.estado == EstadoFactura.aprobada_auto,
                func.date(Factura.fecha_procesamiento_auto) == hoy
            )
        ).scalar() or 0

        facturas_revision_hoy = db.query(func.count(Factura.id)).filter(
            and_(
                Factura.estado == EstadoFactura.en_revision,
                func.date(Factura.fecha_procesamiento_auto) == hoy
            )
        ).scalar() or 0

        facturas_pendientes_total = db.query(func.count(Factura.id)).filter(
            Factura.estado == EstadoFactura.en_revision
        ).scalar() or 0

        # Tasa de automatización del día
        total_procesadas_hoy = facturas_aprobadas_hoy + facturas_revision_hoy
        tasa_automatizacion = (
            (facturas_aprobadas_hoy / total_procesadas_hoy * 100)
            if total_procesadas_hoy > 0 else 0
        )

        # Últimas 10 facturas procesadas automáticamente
        ultimas_facturas = db.query(Factura).filter(
            Factura.fecha_procesamiento_auto.isnot(None)
        ).order_by(
            Factura.fecha_procesamiento_auto.desc()
        ).limit(10).all()

        ultimas_facturas_data = [
            {
                'id': f.id,
                'numero_factura': f.numero_factura,
                'proveedor': f.proveedor.nombre if f.proveedor else 'N/A',
                'total': float(f.total_a_pagar) if f.total_a_pagar else 0,
                'estado': f.estado.value if f.estado else 'pendiente',
                'confianza': float(f.confianza_automatica) if f.confianza_automatica else 0,
                'fecha_procesamiento': f.fecha_procesamiento_auto.isoformat() if f.fecha_procesamiento_auto else None,
                'motivo': f.motivo_decision or 'Sin motivo'
            }
            for f in ultimas_facturas
        ]

        # Estadísticas de la última semana
        fecha_semana = datetime.utcnow() - timedelta(days=7)
        facturas_semana = db.query(func.count(Factura.id)).filter(
            and_(
                Factura.fecha_procesamiento_auto >= fecha_semana,
                Factura.estado.in_([EstadoFactura.aprobada_auto, EstadoFactura.en_revision])
            )
        ).scalar() or 0

        facturas_aprobadas_semana = db.query(func.count(Factura.id)).filter(
            and_(
                Factura.fecha_procesamiento_auto >= fecha_semana,
                Factura.estado == EstadoFactura.aprobada_auto
            )
        ).scalar() or 0

        return {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'metricas_hoy': {
                'facturas_aprobadas_automaticamente': facturas_aprobadas_hoy,
                'facturas_en_revision_manual': facturas_revision_hoy,
                'facturas_pendientes_procesamiento': facturas_pendientes_total,
                'total_procesadas': total_procesadas_hoy,
                'tasa_automatizacion_pct': round(tasa_automatizacion, 1)
            },
            'metricas_semana': {
                'total_procesadas': facturas_semana,
                'aprobadas_automaticamente': facturas_aprobadas_semana,
                'tasa_automatizacion_pct': round(
                    (facturas_aprobadas_semana / facturas_semana * 100) if facturas_semana > 0 else 0,
                    1
                )
            },
            'ultimas_facturas': ultimas_facturas_data,
            'estado_sistema': {
                'automatizacion_activa': True,
                'ultima_ejecucion': ultimas_facturas[0].fecha_procesamiento_auto.isoformat() if ultimas_facturas else None,
                'proxima_ejecucion_programada': 'Cada hora en punto'
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo métricas del dashboard: {str(e)}"
        )


# Función auxiliar para notificaciones en segundo plano
async def enviar_notificaciones_procesamiento(db: Session, resultado_procesamiento: Dict[str, Any]):
    """Envía notificaciones de procesamiento en segundo plano."""
    try:
        # Identificar facturas que requieren notificación
        facturas_revision = []
        facturas_aprobadas = []

        for factura_info in resultado_procesamiento.get('facturas_procesadas', []):
            if factura_info.get('requiere_accion_manual', False):
                facturas_revision.append(factura_info['factura_id'])
            elif factura_info.get('decision') == 'aprobacion_automatica':
                facturas_aprobadas.append(factura_info['factura_id'])

        # Enviar notificaciones para facturas que requieren revisión
        for factura_id in facturas_revision:
            factura = crud_factura.get_factura(db, factura_id)
            if factura:
                notification_service.notificar_revision_requerida(
                    db=db,
                    factura=factura,
                    motivo=factura.motivo_decision or "Requiere revisión manual",
                    confianza=float(factura.confianza_automatica or 0),
                    patron_detectado=factura.patron_recurrencia or "no_detectado"
                )

        # Enviar resumen general si se procesaron facturas
        if resultado_procesamiento['resumen_general']['facturas_procesadas'] > 0:
            facturas_pendientes = crud_factura.get_facturas_pendientes_procesamiento(db)
            notification_service.enviar_resumen_procesamiento(
                db=db,
                estadisticas_procesamiento=resultado_procesamiento,
                facturas_pendientes=facturas_pendientes
            )

    except Exception as e:
        # Registrar error pero no fallar el procesamiento principal
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error enviando notificaciones en segundo plano: {str(e)}")