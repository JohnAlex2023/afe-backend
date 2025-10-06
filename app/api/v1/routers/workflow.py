"""
Router API para Workflow de Aprobación Automática de Facturas.

Endpoints para:
- Procesar facturas nuevas
- Aprobar/Rechazar facturas
- Consultar estado de workflow
- Dashboard de seguimiento
- Gestión de asignaciones NIT-Responsable
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.services.workflow_automatico import WorkflowAutomaticoService
from app.services.notificaciones import NotificacionService
from app.models.workflow_aprobacion import (
    WorkflowAprobacionFactura,
    AsignacionNitResponsable,
    NotificacionWorkflow,
    EstadoFacturaWorkflow
)


router = APIRouter(prefix="/workflow", tags=["Workflow Aprobación"])


# ==================== SCHEMAS ====================

class ProcesarFacturaRequest(BaseModel):
    factura_id: int


class AprobacionManualRequest(BaseModel):
    aprobado_por: str
    observaciones: Optional[str] = None


class RechazoRequest(BaseModel):
    rechazado_por: str
    motivo: str
    detalle: Optional[str] = None


class AsignacionNitRequest(BaseModel):
    nit: str
    nombre_proveedor: Optional[str] = None
    responsable_id: int
    area: Optional[str] = None
    permitir_aprobacion_automatica: bool = True
    requiere_revision_siempre: bool = False
    monto_maximo_auto_aprobacion: Optional[float] = None
    porcentaje_variacion_permitido: float = 5.0
    emails_notificacion: Optional[List[str]] = None


# ==================== ENDPOINTS DE WORKFLOW ====================

@router.post("/procesar-factura")
def procesar_factura_nueva(
    request: ProcesarFacturaRequest,
    db: Session = Depends(get_db)
):
    """
    Procesa una factura recién ingresada al sistema.

    **Flujo automático:**
    1. Identifica NIT del proveedor
    2. Asigna al responsable correspondiente
    3. Compara con factura del mes anterior
    4. Aprueba automáticamente si es idéntica
    5. Envía a revisión manual si hay diferencias
    6. Genera notificaciones
    """
    servicio = WorkflowAutomaticoService(db)
    resultado = servicio.procesar_factura_nueva(request.factura_id)

    if resultado.get("error"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=resultado["error"]
        )

    return resultado


@router.post("/procesar-lote")
def procesar_facturas_pendientes(
    limite: int = Query(default=50, description="Máximo de facturas a procesar"),
    db: Session = Depends(get_db)
):
    """
    Procesa en lote todas las facturas que aún no tienen workflow asignado.
    """
    from app.models.factura import Factura

    # Obtener facturas sin workflow
    facturas_sin_workflow = db.query(Factura).filter(
        ~Factura.id.in_(
            db.query(WorkflowAprobacionFactura.factura_id)
        )
    ).limit(limite).all()

    servicio = WorkflowAutomaticoService(db)
    resultados = {
        "total_procesadas": 0,
        "exitosas": 0,
        "errores": [],
        "workflows_creados": []
    }

    for factura in facturas_sin_workflow:
        resultado = servicio.procesar_factura_nueva(factura.id)

        resultados["total_procesadas"] += 1

        if resultado.get("exito"):
            resultados["exitosas"] += 1
            resultados["workflows_creados"].append({
                "factura_id": factura.id,
                "workflow_id": resultado.get("workflow_id"),
                "estado": resultado.get("estado")
            })
        else:
            resultados["errores"].append({
                "factura_id": factura.id,
                "error": resultado.get("error")
            })

    return resultados


@router.post("/aprobar/{workflow_id}")
def aprobar_factura_manual(
    workflow_id: int,
    request: AprobacionManualRequest,
    db: Session = Depends(get_db)
):
    """
    Aprueba manualmente una factura.

    Usar cuando la factura está en estado PENDIENTE_REVISION.
    """
    servicio = WorkflowAutomaticoService(db)
    resultado = servicio.aprobar_manual(
        workflow_id=workflow_id,
        aprobado_por=request.aprobado_por,
        observaciones=request.observaciones
    )

    if resultado.get("error"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=resultado["error"]
        )

    return resultado


@router.post("/rechazar/{workflow_id}")
def rechazar_factura(
    workflow_id: int,
    request: RechazoRequest,
    db: Session = Depends(get_db)
):
    """
    Rechaza una factura.
    """
    servicio = WorkflowAutomaticoService(db)
    resultado = servicio.rechazar(
        workflow_id=workflow_id,
        rechazado_por=request.rechazado_por,
        motivo=request.motivo,
        detalle=request.detalle
    )

    if resultado.get("error"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=resultado["error"]
        )

    return resultado


@router.get("/consultar/{workflow_id}")
def consultar_workflow(
    workflow_id: int,
    db: Session = Depends(get_db)
):
    """
    Consulta el estado de un workflow específico.
    """
    workflow = db.query(WorkflowAprobacionFactura).filter(
        WorkflowAprobacionFactura.id == workflow_id
    ).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} no encontrado"
        )

    return {
        "workflow_id": workflow.id,
        "factura_id": workflow.factura_id,
        "numero_factura": workflow.factura.numero_factura if workflow.factura else None,
        "estado": workflow.estado.value,
        "estado_anterior": workflow.estado_anterior.value if workflow.estado_anterior else None,
        "nit_proveedor": workflow.nit_proveedor,
        "responsable_id": workflow.responsable_id,
        "area_responsable": workflow.area_responsable,
        "es_identica_mes_anterior": workflow.es_identica_mes_anterior,
        "porcentaje_similitud": float(workflow.porcentaje_similitud) if workflow.porcentaje_similitud else None,
        "diferencias_detectadas": workflow.diferencias_detectadas,
        "criterios_comparacion": workflow.criterios_comparacion,
        "tipo_aprobacion": workflow.tipo_aprobacion.value if workflow.tipo_aprobacion else None,
        "aprobada": workflow.aprobada,
        "aprobada_por": workflow.aprobada_por,
        "fecha_aprobacion": workflow.fecha_aprobacion,
        "observaciones_aprobacion": workflow.observaciones_aprobacion,
        "rechazada": workflow.rechazada,
        "rechazada_por": workflow.rechazada_por,
        "fecha_rechazo": workflow.fecha_rechazo,
        "motivo_rechazo": workflow.motivo_rechazo.value if workflow.motivo_rechazo else None,
        "detalle_rechazo": workflow.detalle_rechazo,
        "tiempo_en_analisis": workflow.tiempo_en_analisis,
        "tiempo_en_revision": workflow.tiempo_en_revision,
        "tiempo_total_aprobacion": workflow.tiempo_total_aprobacion,
        "recordatorios_enviados": workflow.recordatorios_enviados,
        "creado_en": workflow.creado_en,
        "actualizado_en": workflow.actualizado_en
    }


@router.get("/listar")
def listar_workflows(
    skip: int = 0,
    limit: int = 100,
    estado: Optional[str] = None,
    responsable_id: Optional[int] = None,
    nit_proveedor: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista workflows con filtros opcionales.
    """
    query = db.query(WorkflowAprobacionFactura)

    if estado:
        try:
            estado_enum = EstadoFacturaWorkflow[estado.upper()]
            query = query.filter(WorkflowAprobacionFactura.estado == estado_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {estado}"
            )

    if responsable_id:
        query = query.filter(WorkflowAprobacionFactura.responsable_id == responsable_id)

    if nit_proveedor:
        query = query.filter(WorkflowAprobacionFactura.nit_proveedor == nit_proveedor)

    workflows = query.order_by(
        WorkflowAprobacionFactura.creado_en.desc()
    ).offset(skip).limit(limit).all()

    return [
        {
            "workflow_id": w.id,
            "factura_id": w.factura_id,
            "numero_factura": w.factura.numero_factura if w.factura else None,
            "estado": w.estado.value,
            "nit_proveedor": w.nit_proveedor,
            "responsable_id": w.responsable_id,
            "area": w.area_responsable,
            "aprobada": w.aprobada,
            "rechazada": w.rechazada,
            "creado_en": w.creado_en
        }
        for w in workflows
    ]


# ==================== DASHBOARD Y ESTADÍSTICAS ====================

@router.get("/dashboard")
def obtener_dashboard_workflow(
    responsable_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Dashboard de seguimiento del workflow de facturas.

    Métricas:
    - Total facturas por estado
    - Facturas aprobadas automáticamente vs manualmente
    - Facturas pendientes de revisión
    - Tiempo promedio de aprobación
    - Facturas rechazadas
    """
    from sqlalchemy import func

    query = db.query(WorkflowAprobacionFactura)

    if responsable_id:
        query = query.filter(WorkflowAprobacionFactura.responsable_id == responsable_id)

    # Contar por estado
    facturas_por_estado = {}
    for estado in EstadoFacturaWorkflow:
        count = query.filter(WorkflowAprobacionFactura.estado == estado).count()
        facturas_por_estado[estado.value] = count

    # Estadísticas de aprobación
    total_aprobadas_auto = query.filter(
        WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.APROBADA_AUTO
    ).count()

    total_aprobadas_manual = query.filter(
        WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.APROBADA_MANUAL
    ).count()

    total_rechazadas = query.filter(
        WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.RECHAZADA
    ).count()

    total_pendientes = query.filter(
        WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.PENDIENTE_REVISION
    ).count()

    # Tiempo promedio de aprobación
    tiempo_promedio = db.query(
        func.avg(WorkflowAprobacionFactura.tiempo_total_aprobacion)
    ).filter(
        WorkflowAprobacionFactura.aprobada == True
    ).scalar() or 0

    # Facturas pendientes hace más de 3 días
    from datetime import datetime, timedelta
    fecha_limite = datetime.now() - timedelta(days=3)

    pendientes_antiguas = query.filter(
        WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.PENDIENTE_REVISION,
        WorkflowAprobacionFactura.fecha_cambio_estado <= fecha_limite
    ).count()

    return {
        "facturas_por_estado": facturas_por_estado,
        "total_aprobadas_automaticamente": total_aprobadas_auto,
        "total_aprobadas_manualmente": total_aprobadas_manual,
        "total_rechazadas": total_rechazadas,
        "total_pendientes_revision": total_pendientes,
        "pendientes_hace_mas_3_dias": pendientes_antiguas,
        "tiempo_promedio_aprobacion_segundos": int(tiempo_promedio),
        "tiempo_promedio_aprobacion_horas": round(tiempo_promedio / 3600, 2) if tiempo_promedio else 0
    }


# ==================== ASIGNACIONES NIT-RESPONSABLE ====================

@router.post("/asignaciones")
def crear_asignacion_nit(
    asignacion: AsignacionNitRequest,
    db: Session = Depends(get_db)
):
    """
    Crea una asignación de NIT a Responsable.

    Configura qué responsable debe aprobar las facturas de un proveedor específico.
    """
    # Verificar si ya existe
    existente = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.nit == asignacion.nit
    ).first()

    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una asignación para el NIT {asignacion.nit}"
        )

    from decimal import Decimal

    nueva_asignacion = AsignacionNitResponsable(
        nit=asignacion.nit,
        nombre_proveedor=asignacion.nombre_proveedor,
        responsable_id=asignacion.responsable_id,
        area=asignacion.area,
        permitir_aprobacion_automatica=asignacion.permitir_aprobacion_automatica,
        requiere_revision_siempre=asignacion.requiere_revision_siempre,
        monto_maximo_auto_aprobacion=Decimal(str(asignacion.monto_maximo_auto_aprobacion)) if asignacion.monto_maximo_auto_aprobacion else None,
        porcentaje_variacion_permitido=Decimal(str(asignacion.porcentaje_variacion_permitido)),
        emails_notificacion=asignacion.emails_notificacion,
        activo=True,
        creado_en=datetime.now()
    )

    db.add(nueva_asignacion)
    db.commit()
    db.refresh(nueva_asignacion)

    return {
        "id": nueva_asignacion.id,
        "nit": nueva_asignacion.nit,
        "responsable_id": nueva_asignacion.responsable_id,
        "mensaje": "Asignación creada exitosamente"
    }


@router.get("/asignaciones")
def listar_asignaciones(
    skip: int = 0,
    limit: int = 100,
    activo: Optional[bool] = True,
    db: Session = Depends(get_db)
):
    """
    Lista todas las asignaciones NIT-Responsable.
    """
    query = db.query(AsignacionNitResponsable)

    if activo is not None:
        query = query.filter(AsignacionNitResponsable.activo == activo)

    asignaciones = query.offset(skip).limit(limit).all()

    return [
        {
            "id": a.id,
            "nit": a.nit,
            "nombre_proveedor": a.nombre_proveedor,
            "responsable_id": a.responsable_id,
            "area": a.area,
            "permitir_aprobacion_automatica": a.permitir_aprobacion_automatica,
            "requiere_revision_siempre": a.requiere_revision_siempre,
            "monto_maximo_auto_aprobacion": float(a.monto_maximo_auto_aprobacion) if a.monto_maximo_auto_aprobacion else None,
            "porcentaje_variacion_permitido": float(a.porcentaje_variacion_permitido),
            "emails_notificacion": a.emails_notificacion,
            "activo": a.activo
        }
        for a in asignaciones
    ]


@router.put("/asignaciones/{asignacion_id}")
def actualizar_asignacion(
    asignacion_id: int,
    asignacion: AsignacionNitRequest,
    db: Session = Depends(get_db)
):
    """
    Actualiza una asignación NIT-Responsable.
    """
    asignacion_db = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.id == asignacion_id
    ).first()

    if not asignacion_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación {asignacion_id} no encontrada"
        )

    from decimal import Decimal
    from datetime import datetime

    asignacion_db.responsable_id = asignacion.responsable_id
    asignacion_db.area = asignacion.area
    asignacion_db.nombre_proveedor = asignacion.nombre_proveedor
    asignacion_db.permitir_aprobacion_automatica = asignacion.permitir_aprobacion_automatica
    asignacion_db.requiere_revision_siempre = asignacion.requiere_revision_siempre
    asignacion_db.monto_maximo_auto_aprobacion = Decimal(str(asignacion.monto_maximo_auto_aprobacion)) if asignacion.monto_maximo_auto_aprobacion else None
    asignacion_db.porcentaje_variacion_permitido = Decimal(str(asignacion.porcentaje_variacion_permitido))
    asignacion_db.emails_notificacion = asignacion.emails_notificacion
    asignacion_db.actualizado_en = datetime.now()

    db.commit()

    return {"mensaje": "Asignación actualizada exitosamente"}


# ==================== NOTIFICACIONES ====================

@router.post("/notificaciones/enviar-pendientes")
def enviar_notificaciones_pendientes(
    limite: int = Query(default=50, description="Máximo de notificaciones a enviar"),
    db: Session = Depends(get_db)
):
    """
    Envía las notificaciones pendientes en cola.
    """
    servicio = NotificacionService(db)
    resultado = servicio.enviar_notificaciones_pendientes(limite)

    return resultado


@router.post("/notificaciones/enviar-recordatorios")
def enviar_recordatorios(
    dias_pendiente: int = Query(default=3, description="Días que debe estar pendiente"),
    db: Session = Depends(get_db)
):
    """
    Envía recordatorios para facturas pendientes de revisión hace más de X días.
    """
    servicio = NotificacionService(db)
    resultado = servicio.enviar_recordatorios_facturas_pendientes(dias_pendiente)

    return resultado


# ==================== ENDPOINTS ADICIONALES ÚTILES ====================

@router.get("/mis-facturas-pendientes")
def obtener_mis_facturas_pendientes(
    responsable_id: int = Query(..., description="ID del responsable"),
    limite: int = Query(default=50, description="Límite de resultados"),
    db: Session = Depends(get_db)
):
    """
    Obtiene todas las facturas pendientes de aprobación de un responsable específico.

    Retorna workflows en estados: PENDIENTE_REVISION, EN_ANALISIS, REQUIERE_APROBACION_MANUAL
    """
    from app.models.factura import Factura

    workflows = db.query(WorkflowAprobacionFactura).join(
        Factura, WorkflowAprobacionFactura.factura_id == Factura.id
    ).filter(
        WorkflowAprobacionFactura.responsable_id == responsable_id,
        WorkflowAprobacionFactura.estado.in_([
            EstadoFacturaWorkflow.PENDIENTE_REVISION,
            EstadoFacturaWorkflow.EN_ANALISIS,
            EstadoFacturaWorkflow.EN_REVISION
        ])
    ).limit(limite).all()

    resultado = []
    for wf in workflows:
        factura = wf.factura
        proveedor_nombre = factura.proveedor.razon_social if factura.proveedor else "Sin proveedor"

        resultado.append({
            "workflow_id": wf.id,
            "factura_id": wf.factura_id,
            "numero_factura": factura.numero_factura,
            "proveedor": proveedor_nombre,
            "nit": wf.nit_proveedor,
            "monto": float(factura.total) if factura.total else 0,
            "fecha_emision": str(factura.fecha_emision) if factura.fecha_emision else None,
            "estado": wf.estado.value,
            "es_identica_mes_anterior": wf.es_identica_mes_anterior,
            "porcentaje_similitud": float(wf.porcentaje_similitud) if wf.porcentaje_similitud else None,
            "fecha_asignacion": str(wf.fecha_asignacion) if wf.fecha_asignacion else None,
            "dias_pendiente": (wf.fecha_asignacion.date() - wf.creado_en.date()).days if wf.fecha_asignacion and wf.creado_en else 0
        })

    return {
        "total": len(resultado),
        "responsable_id": responsable_id,
        "facturas_pendientes": resultado
    }


@router.get("/factura-detalle/{factura_id}")
def obtener_factura_con_workflow(
    factura_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene el detalle completo de una factura incluyendo su workflow y comparación.

    Útil para mostrar toda la información en un dashboard o modal de aprobación.
    """
    from app.models.factura import Factura

    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    workflow = db.query(WorkflowAprobacionFactura).filter(
        WorkflowAprobacionFactura.factura_id == factura_id
    ).first()

    proveedor_info = None
    if factura.proveedor:
        proveedor_info = {
            "nit": factura.proveedor.nit,
            "razon_social": factura.proveedor.razon_social,
            "area": factura.proveedor.area
        }

    factura_detalle = {
        "id": factura.id,
        "numero_factura": factura.numero_factura,
        "cufe": factura.cufe,
        "fecha_emision": str(factura.fecha_emision) if factura.fecha_emision else None,
        "proveedor": proveedor_info,
        "subtotal": float(factura.subtotal) if factura.subtotal else 0,
        "iva": float(factura.iva) if factura.iva else 0,
        "total": float(factura.total) if factura.total else 0,
        "total_a_pagar": float(factura.total_a_pagar) if factura.total_a_pagar else 0,
        "moneda": factura.moneda,
        "estado": factura.estado.value,
        "observaciones": factura.observaciones,
        "periodo_factura": factura.periodo_factura
    }

    workflow_info = None
    if workflow:
        factura_anterior = None
        if workflow.factura_mes_anterior_id:
            factura_anterior = db.query(Factura).filter(
                Factura.id == workflow.factura_mes_anterior_id
            ).first()

        workflow_info = {
            "id": workflow.id,
            "estado": workflow.estado.value,
            "tipo_aprobacion": workflow.tipo_aprobacion.value if workflow.tipo_aprobacion else None,
            "responsable_id": workflow.responsable_id,
            "area_responsable": workflow.area_responsable,
            "es_identica_mes_anterior": workflow.es_identica_mes_anterior,
            "porcentaje_similitud": float(workflow.porcentaje_similitud) if workflow.porcentaje_similitud else None,
            "diferencias_detectadas": workflow.diferencias_detectadas,
            "criterios_comparacion": workflow.criterios_comparacion,
            "fecha_aprobacion": str(workflow.fecha_aprobacion) if workflow.fecha_aprobacion else None,
            "aprobado_por": workflow.aprobado_por,
            "fecha_rechazo": str(workflow.fecha_rechazo) if workflow.fecha_rechazo else None,
            "rechazado_por": workflow.rechazado_por,
            "motivo_rechazo": workflow.motivo_rechazo,
            "factura_mes_anterior": {
                "id": factura_anterior.id,
                "numero": factura_anterior.numero_factura,
                "total": float(factura_anterior.total) if factura_anterior.total else 0,
                "fecha": str(factura_anterior.fecha_emision) if factura_anterior.fecha_emision else None
            } if factura_anterior else None
        }

    return {
        "factura": factura_detalle,
        "workflow": workflow_info,
        "tiene_workflow": workflow is not None
    }
