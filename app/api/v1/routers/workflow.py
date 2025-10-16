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


@router.post("/factura/aprobar/{factura_id}")
def aprobar_por_factura_id(
    factura_id: int,
    request: AprobacionManualRequest,
    db: Session = Depends(get_db)
):
    """
    Aprueba una factura usando su factura_id.

    Este endpoint es útil cuando se trabaja directamente con facturas
    que aún no tienen workflow creado. Si no existe workflow, lo crea automáticamente.
    """
    from app.models.factura import Factura

    # Verificar que la factura existe
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Factura {factura_id} no encontrada"
        )

    # Buscar o crear workflow
    workflow = db.query(WorkflowAprobacionFactura).filter(
        WorkflowAprobacionFactura.factura_id == factura_id
    ).first()

    if not workflow:
        # Crear workflow automáticamente
        servicio = WorkflowAutomaticoService(db)
        resultado_proceso = servicio.procesar_factura_nueva(factura_id)

        if resultado_proceso.get("error"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al procesar factura: {resultado_proceso['error']}"
            )

        # Obtener el workflow recién creado
        workflow = db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.factura_id == factura_id
        ).first()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear workflow para la factura"
            )

    # Aprobar usando el workflow_id
    servicio = WorkflowAutomaticoService(db)
    resultado = servicio.aprobar_manual(
        workflow_id=workflow.id,
        aprobado_por=request.aprobado_por,
        observaciones=request.observaciones
    )

    if resultado.get("error"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=resultado["error"]
        )

    return resultado


@router.post("/factura/rechazar/{factura_id}")
def rechazar_por_factura_id(
    factura_id: int,
    request: RechazoRequest,
    db: Session = Depends(get_db)
):
    """
    Rechaza una factura usando su factura_id.

    Este endpoint es útil cuando se trabaja directamente con facturas
    que aún no tienen workflow creado. Si no existe workflow, lo crea automáticamente.
    """
    from app.models.factura import Factura

    # Verificar que la factura existe
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Factura {factura_id} no encontrada"
        )

    # Buscar o crear workflow
    workflow = db.query(WorkflowAprobacionFactura).filter(
        WorkflowAprobacionFactura.factura_id == factura_id
    ).first()

    if not workflow:
        # Crear workflow automáticamente
        servicio = WorkflowAutomaticoService(db)
        resultado_proceso = servicio.procesar_factura_nueva(factura_id)

        if resultado_proceso.get("error"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al procesar factura: {resultado_proceso['error']}"
            )

        # Obtener el workflow recién creado
        workflow = db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.factura_id == factura_id
        ).first()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear workflow para la factura"
            )

    # Rechazar usando el workflow_id
    servicio = WorkflowAutomaticoService(db)
    resultado = servicio.rechazar(
        workflow_id=workflow.id,
        rechazado_por=request.rechazado_por,
        motivo=request.motivo,
        detalle=request.detalle
    )

    if resultado.get("error"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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

    total_en_revision = query.filter(
        WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.EN_REVISION
    ).count()

    # Total de aprobadas (manual + auto)
    total_aprobadas = total_aprobadas_auto + total_aprobadas_manual

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

    # Calcular tasa de aprobación automática
    total_facturas = total_aprobadas + total_rechazadas + total_pendientes + total_en_revision
    tasa_aprobacion_automatica = (total_aprobadas_auto / total_facturas * 100) if total_facturas > 0 else 0

    return {
        # Campos compatibles con el frontend
        "total_pendientes": total_pendientes,
        "total_en_revision": total_en_revision,
        "total_aprobadas": total_aprobadas,
        "total_aprobadas_auto": total_aprobadas_auto,
        "total_rechazadas": total_rechazadas,
        "pendientes_antiguas": pendientes_antiguas,
        "tiempo_promedio_aprobacion_horas": round(tiempo_promedio / 3600, 2) if tiempo_promedio else 0,
        "tasa_aprobacion_automatica": round(tasa_aprobacion_automatica, 2),

        # Campos adicionales para compatibilidad legacy
        "facturas_por_estado": facturas_por_estado,
        "total_aprobadas_automaticamente": total_aprobadas_auto,
        "total_aprobadas_manualmente": total_aprobadas_manual,
        "total_pendientes_revision": total_pendientes,
        "pendientes_hace_mas_3_dias": pendientes_antiguas,
        "tiempo_promedio_aprobacion_segundos": int(tiempo_promedio),
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
    from datetime import datetime

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
    from app.models.responsable import Responsable
    from sqlalchemy.orm import joinedload

    workflows = db.query(WorkflowAprobacionFactura).join(
        Factura, WorkflowAprobacionFactura.factura_id == Factura.id
    ).options(
        joinedload(WorkflowAprobacionFactura.factura).joinedload(Factura.responsable)
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

        # 🔥 Obtener nombre del responsable asignado
        nombre_responsable = None
        if factura.responsable:
            nombre_responsable = factura.responsable.nombre

        resultado.append({
            "workflow_id": wf.id,
            "factura_id": wf.factura_id,
            "numero_factura": factura.numero_factura,
            "proveedor": proveedor_nombre,
            "nit": wf.nit_proveedor,
            "monto": float(factura.total_a_pagar) if factura.total_a_pagar else 0,
            "fecha_emision": str(factura.fecha_emision) if factura.fecha_emision else None,
            "estado": wf.estado.value,
            "es_identica_mes_anterior": wf.es_identica_mes_anterior,
            "porcentaje_similitud": float(wf.porcentaje_similitud) if wf.porcentaje_similitud else None,
            "fecha_asignacion": str(wf.fecha_asignacion) if wf.fecha_asignacion else None,
            "dias_pendiente": (wf.fecha_asignacion.date() - wf.creado_en.date()).days if wf.fecha_asignacion and wf.creado_en else 0,
            # Campo de auditoría para ADMIN
            "nombre_responsable": nombre_responsable
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
    from app.services.analisis_patrones import AnalizadorPatrones

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

    # Calcular año/mes desde fecha_emision
    año = factura.fecha_emision.year if factura.fecha_emision else None
    mes = factura.fecha_emision.month if factura.fecha_emision else None

    factura_detalle = {
        "id": factura.id,
        "numero_factura": factura.numero_factura,
        "cufe": factura.cufe,
        "fecha_emision": str(factura.fecha_emision) if factura.fecha_emision else None,
        "fecha_vencimiento": str(factura.fecha_vencimiento) if factura.fecha_vencimiento else None,
        "año": año,
        "mes": mes,
        "proveedor": proveedor_info,
        "subtotal": float(factura.subtotal) if factura.subtotal else 0,
        "iva": float(factura.iva) if factura.iva else 0,
        "total_a_pagar": float(factura.total_a_pagar) if factura.total_a_pagar else 0,
        "estado": factura.estado.value,
        "cantidad_items": len(factura.items) if factura.items else 0
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
            "aprobado_por": workflow.aprobada_por,
            "fecha_rechazo": str(workflow.fecha_rechazo) if workflow.fecha_rechazo else None,
            "rechazado_por": workflow.rechazada_por,
            "motivo_rechazo": workflow.motivo_rechazo,
            "factura_mes_anterior": {
                "id": factura_anterior.id,
                "numero_factura": factura_anterior.numero_factura,
                "fecha_emision": str(factura_anterior.fecha_emision) if factura_anterior.fecha_emision else None,
                "fecha_vencimiento": str(factura_anterior.fecha_vencimiento) if factura_anterior.fecha_vencimiento else None,
                "subtotal": float(factura_anterior.subtotal) if factura_anterior.subtotal else 0,
                "iva": float(factura_anterior.iva) if factura_anterior.iva else 0,
                "total": float(factura_anterior.total) if factura_anterior.total else 0,
                "total_a_pagar": float(factura_anterior.total_a_pagar) if factura_anterior.total_a_pagar else 0
            } if factura_anterior else None
        }

    # ✨ NUEVO: Análisis de patrones históricos
    contexto_historico = None
    try:
        if factura.concepto_normalizado and factura.proveedor_id:
            analizador = AnalizadorPatrones(db)
            historial, recomendacion = analizador.evaluar_factura_nueva(factura)

            if historial:
                contexto_historico = {
                    "tipo_patron": historial.tipo_patron.value,
                    "recomendacion": recomendacion["recomendacion"],
                    "motivo": recomendacion["motivo"],
                    "confianza": recomendacion["confianza"],
                    "estadisticas": {
                        "pagos_analizados": historial.pagos_analizados,
                        "meses_con_pagos": historial.meses_con_pagos,
                        "monto_promedio": float(historial.monto_promedio),
                        "monto_minimo": float(historial.monto_minimo),
                        "monto_maximo": float(historial.monto_maximo),
                        "coeficiente_variacion": float(historial.coeficiente_variacion),
                    },
                    "rango_esperado": {
                        "inferior": float(historial.rango_inferior) if historial.rango_inferior else None,
                        "superior": float(historial.rango_superior) if historial.rango_superior else None,
                    } if historial.rango_inferior else None,
                    "ultimo_pago": {
                        "fecha": str(historial.ultimo_pago_fecha) if historial.ultimo_pago_fecha else None,
                        "monto": float(historial.ultimo_pago_monto) if historial.ultimo_pago_monto else None,
                    } if historial.ultimo_pago_fecha else None,
                    "pagos_historicos": historial.pagos_detalle[:6] if historial.pagos_detalle else [],
                    "contexto_adicional": recomendacion["contexto"]
                }
    except Exception as e:
        # Si falla el análisis de patrones, simplemente no incluir contexto histórico
        # La factura detalle se retorna normalmente sin esta información adicional
        print(f"Warning: Error en análisis de patrones para factura {factura_id}: {str(e)}")
        contexto_historico = None

    return {
        "factura": factura_detalle,
        "workflow": workflow_info,
        "contexto_historico": contexto_historico,
        "tiene_workflow": workflow is not None
    }


@router.post("/analizar-patrones/{proveedor_id}")
def analizar_patron_proveedor(
    proveedor_id: int,
    concepto: str = Query(..., description="Concepto normalizado a analizar"),
    db: Session = Depends(get_db)
):
    """
    Analiza el patrón histórico de pagos para un proveedor y concepto específico.

    Genera estadísticas y clasificación (Tipo A, B, C) basado en los últimos 12 meses.
    """
    from app.services.analisis_patrones import AnalizadorPatrones

    analizador = AnalizadorPatrones(db)
    concepto_normalizado = analizador.normalizar_concepto(concepto)

    historial = analizador.analizar_proveedor_concepto(
        proveedor_id,
        concepto_normalizado,
        guardar=True
    )

    if not historial:
        return {
            "tipo_patron": "TIPO_C",
            "mensaje": "Sin historial de pagos para este proveedor y concepto",
            "pagos_analizados": 0
        }

    return {
        "tipo_patron": historial.tipo_patron.value,
        "concepto_normalizado": historial.concepto_normalizado,
        "estadisticas": {
            "pagos_analizados": historial.pagos_analizados,
            "meses_con_pagos": historial.meses_con_pagos,
            "monto_promedio": float(historial.monto_promedio),
            "monto_minimo": float(historial.monto_minimo),
            "monto_maximo": float(historial.monto_maximo),
            "desviacion_estandar": float(historial.desviacion_estandar),
            "coeficiente_variacion": float(historial.coeficiente_variacion),
        },
        "rango_esperado": {
            "inferior": float(historial.rango_inferior) if historial.rango_inferior else None,
            "superior": float(historial.rango_superior) if historial.rango_superior else None,
        } if historial.rango_inferior else None,
        "puede_aprobar_automaticamente": bool(historial.puede_aprobar_auto),
        "pagos_historicos": historial.pagos_detalle[:12] if historial.pagos_detalle else [],
        "fecha_analisis": str(historial.fecha_analisis),
    }


@router.post("/regenerar-patrones")
def regenerar_todos_patrones(
    limit: Optional[int] = Query(None, description="Límite de combinaciones a procesar"),
    db: Session = Depends(get_db)
):
    """
    Regenera todos los patrones históricos del sistema.

    Útil para:
    - Inicialización del sistema
    - Recalibración después de cambios en algoritmo
    - Actualización masiva de patrones
    """
    from app.services.analisis_patrones import AnalizadorPatrones

    analizador = AnalizadorPatrones(db)

    try:
        analizador.regenerar_todos_patrones(limit=limit)

        # Contar patrones generados
        from app.models.historial_pagos import HistorialPagos, TipoPatron

        total = db.query(HistorialPagos).count()
        tipo_a = db.query(HistorialPagos).filter(
            HistorialPagos.tipo_patron == TipoPatron.TIPO_A
        ).count()
        tipo_b = db.query(HistorialPagos).filter(
            HistorialPagos.tipo_patron == TipoPatron.TIPO_B
        ).count()
        tipo_c = db.query(HistorialPagos).filter(
            HistorialPagos.tipo_patron == TipoPatron.TIPO_C
        ).count()

        return {
            "exito": True,
            "mensaje": "Patrones regenerados exitosamente",
            "total_patrones": total,
            "distribucion": {
                "tipo_a_fijo": tipo_a,
                "tipo_b_fluctuante": tipo_b,
                "tipo_c_excepcional": tipo_c
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error regenerando patrones: {str(e)}"
        )


# ==================== ENDPOINT ENTERPRISE: COMPARACIÓN DE ITEMS ====================

@router.post("/comparar-factura-items/{factura_id}")
def comparar_factura_items(
    factura_id: int,
    meses_historico: int = Query(default=12, description="Meses de historial a analizar"),
    db: Session = Depends(get_db)
):
    """
    🔬 **ENDPOINT ENTERPRISE: Comparación Granular Item por Item**

    Analiza una factura comparando cada item contra su historial mensual.

    **Funcionalidad:**
    - Compara item por item vs histórico del proveedor
    - Detecta variaciones de precio unitario (umbrales: 15% moderado, 30% alto)
    - Detecta variaciones de cantidad (umbrales: 20% moderado, 50% alto)
    - Identifica items nuevos sin historial
    - Genera alertas con severidad (baja/media/alta)
    - Calcula confianza para aprobación automática (0-100%)

    **Retorna:**
    - Análisis detallado de cada item
    - Alertas organizadas por severidad
    - Recomendación de aprobación (aprobar_auto / en_revision)
    - Porcentaje de confianza

    **Uso:**
    - Verificación manual antes de aprobar factura
    - Auditoría de facturas ya procesadas
    - Análisis de proveedores con cambios frecuentes
    """
    from app.services.comparador_items import ComparadorItemsService
    from datetime import datetime

    try:
        comparador = ComparadorItemsService(db)

        resultado = comparador.comparar_factura_vs_historial(
            factura_id=factura_id,
            meses_historico=meses_historico
        )

        return {
            "exito": True,
            "factura_id": factura_id,
            "analisis": resultado,
            "timestamp": datetime.now().isoformat()
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en análisis de items: {str(e)}"
        )


@router.get("/estadisticas-comparacion")
def obtener_estadisticas_comparacion(
    fecha_desde: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    📊 **Estadísticas del Sistema de Comparación de Items**

    Retorna métricas globales del sistema de comparación automática.

    **Métricas:**
    - Total de facturas analizadas
    - Tasa de aprobación automática
    - Alertas más comunes
    - Proveedores con más variaciones
    - Tendencias de precios
    """
    from datetime import datetime as dt

    # Parsear fechas
    fecha_desde_dt = dt.fromisoformat(fecha_desde) if fecha_desde else dt(2024, 1, 1)
    fecha_hasta_dt = dt.fromisoformat(fecha_hasta) if fecha_hasta else dt.now()

    # Consultar workflows en el rango
    workflows = db.query(WorkflowAprobacionFactura).filter(
        WorkflowAprobacionFactura.creado_en >= fecha_desde_dt,
        WorkflowAprobacionFactura.creado_en <= fecha_hasta_dt
    ).all()

    total_analizadas = len(workflows)
    total_aprobadas_auto = sum(1 for w in workflows if w.estado == EstadoFacturaWorkflow.APROBADA_AUTO)
    total_revision_manual = sum(1 for w in workflows if w.estado == EstadoFacturaWorkflow.PENDIENTE_REVISION)

    # Calcular tasa de aprobación automática
    tasa_aprobacion_auto = (total_aprobadas_auto / total_analizadas * 100) if total_analizadas > 0 else 0

    # Recopilar alertas
    todas_alertas = []
    for w in workflows:
        if w.diferencias_detectadas:
            todas_alertas.extend(w.diferencias_detectadas)

    # Contar alertas por tipo
    from collections import Counter
    alertas_por_tipo = Counter(a.get('tipo', 'desconocido') for a in todas_alertas)

    return {
        "periodo": {
            "desde": fecha_desde_dt.isoformat(),
            "hasta": fecha_hasta_dt.isoformat()
        },
        "metricas_generales": {
            "total_facturas_analizadas": total_analizadas,
            "total_aprobadas_automaticamente": total_aprobadas_auto,
            "total_revision_manual": total_revision_manual,
            "tasa_aprobacion_automatica_pct": round(tasa_aprobacion_auto, 2)
        },
        "alertas": {
            "total_alertas": len(todas_alertas),
            "alertas_por_tipo": dict(alertas_por_tipo.most_common(10))
        }
    }
