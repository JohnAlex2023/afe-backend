# app/api/v1/routers/accounting.py
"""
Router para operaciones de contabilidad.

Endpoints accesibles solo para usuarios con rol 'contador'.
Gestiona operaciones específicas del departamento de contabilidad.

Autor: Equipo Senior de Desarrollo
Fecha: 2025-11-18
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.core.security import require_role
from app.schemas.devolucion import DevolucionRequest, DevolucionResponse
from app.schemas.common import ErrorResponse
from app.models.factura import Factura, EstadoFactura
from app.models.workflow_aprobacion import WorkflowAprobacionFactura
from app.services.unified_email_service import UnifiedEmailService
from app.services.email_template_service import EmailTemplateService
from app.core.config import settings
from app.utils.logger import logger


router = APIRouter(tags=["Contabilidad"])


@router.post(
    "/facturas/{factura_id}/devolver",
    response_model=DevolucionResponse,
    summary="Devolver factura al proveedor",
    description="""
    Devuelve una factura al proveedor solicitando información adicional.

    **Permisos:** Solo usuarios con rol 'contador' pueden ejecutar esta acción.

    **Flujo:**
    1. Contador encuentra que una factura aprobada necesita información adicional
    2. Usa este endpoint especificando qué información falta
    3. Sistema envía emails a:
       - Proveedor (solicitando la información)
       - Responsable que aprobó (notificación informativa)
    4. Cambia el estado de la factura a 'devuelta'

    **Nota:** La factura debe estar en estado 'aprobada' o 'aprobada_auto' para poder devolverla.
    """,
    responses={
        200: {
            "description": "Factura devuelta exitosamente",
            "model": DevolucionResponse
        },
        400: {
            "model": ErrorResponse,
            "description": "Factura no puede ser devuelta (estado inválido)"
        },
        403: {
            "model": ErrorResponse,
            "description": "Sin permisos (solo contador)"
        },
        404: {
            "model": ErrorResponse,
            "description": "Factura no encontrada"
        }
    }
)
async def devolver_factura(
    factura_id: int,
    request: DevolucionRequest,
    current_user=Depends(require_role("contador")),
    db: Session = Depends(get_db)
):
    """
    Endpoint profesional para devolver facturas.

    Enterprise features:
    - Validación de estados
    - Notificación automática a proveedor y responsable
    - Auditoría completa
    - Logging detallado
    """

    # ========================================================================
    # VALIDACIONES
    # ========================================================================

    # Obtener factura
    factura = db.query(Factura).filter(Factura.id == factura_id).first()

    if not factura:
        logger.warning(
            f"Intento de devolver factura inexistente: {factura_id}",
            extra={"factura_id": factura_id, "contador": current_user.usuario}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Factura con ID {factura_id} no encontrada"
        )

    # Validar que la factura esté aprobada
    if factura.estado not in [EstadoFactura.aprobada, EstadoFactura.aprobada_auto]:
        logger.warning(
            f"Intento de devolver factura en estado inválido: {factura.estado.value}",
            extra={
                "factura_id": factura_id,
                "estado": factura.estado.value,
                "contador": current_user.usuario
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede devolver una factura en estado '{factura.estado.value}'. "
                   f"Solo se pueden devolver facturas aprobadas."
        )

    # Obtener workflow para saber quién aprobó
    workflow = (
        db.query(WorkflowAprobacionFactura)
        .filter(WorkflowAprobacionFactura.factura_id == factura_id)
        .first()
    )

    # ========================================================================
    # PREPARAR INFORMACIÓN PARA EMAILS
    # ========================================================================

    numero_factura = factura.numero_factura or "Sin número"
    nombre_proveedor = (
        factura.proveedor.razon_social if factura.proveedor else "Proveedor desconocido"
    )
    nit_proveedor = factura.proveedor.nit if factura.proveedor else "N/A"

    # Formatear monto
    if factura.total_a_pagar:
        monto_factura = f"${factura.total_a_pagar:,.2f} COP"
    elif factura.total_calculado:
        monto_factura = f"${factura.total_calculado:,.2f} COP"
    else:
        monto_factura = "N/A"

    fecha_devolucion = datetime.now().strftime("%d/%m/%Y %H:%M")
    devuelto_por = current_user.nombre if hasattr(current_user, 'nombre') else current_user.usuario

    # Email del proveedor (si existe)
    email_proveedor = factura.proveedor.contacto_email if factura.proveedor else None

    # Email del responsable que aprobó
    email_responsable = None
    nombre_responsable = "Responsable"
    if workflow and workflow.responsable:
        email_responsable = workflow.responsable.email
        nombre_responsable = workflow.responsable.nombre or workflow.responsable.usuario

    # ========================================================================
    # ENVIAR NOTIFICACIONES
    # ========================================================================

    email_service = UnifiedEmailService()
    template_service = EmailTemplateService()

    destinatarios_notificados = []
    notificaciones_exitosas = 0

    # Enviar email al proveedor (si está configurado y usuario lo solicita)
    if request.notificar_proveedor and email_proveedor:
        try:
            context = {
                "numero_factura": numero_factura,
                "nombre_proveedor": nombre_proveedor,
                "nit_proveedor": nit_proveedor,
                "monto_factura": monto_factura,
                "fecha_devolucion": fecha_devolucion,
                "devuelto_por": devuelto_por,
                "observaciones_devolucion": request.observaciones
            }

            html_content = template_service.render_template(
                "devolucion_factura_proveedor.html",
                context
            )

            email_service.send_email(
                to_email=email_proveedor,
                subject=f"⚠️ Factura {numero_factura} - Información adicional requerida",
                body_html=html_content
            )

            destinatarios_notificados.append(email_proveedor)
            notificaciones_exitosas += 1

            logger.info(
                f"Email de devolución enviado a proveedor: {email_proveedor}",
                extra={"factura_id": factura_id, "proveedor_email": email_proveedor}
            )

        except Exception as e:
            logger.error(
                f"Error enviando email a proveedor {email_proveedor}: {str(e)}",
                exc_info=True,
                extra={"factura_id": factura_id}
            )
            # Continuar aunque falle el email al proveedor

    # Enviar email al responsable (si usuario lo solicita)
    if request.notificar_responsable and email_responsable:
        try:
            context = {
                "nombre_responsable": nombre_responsable,
                "numero_factura": numero_factura,
                "nombre_proveedor": nombre_proveedor,
                "nit_proveedor": nit_proveedor,
                "monto_factura": monto_factura,
                "fecha_devolucion": fecha_devolucion,
                "devuelto_por": devuelto_por,
                "observaciones_devolucion": request.observaciones
            }

            html_content = template_service.render_template(
                "devolucion_factura_responsable.html",
                context
            )

            email_service.send_email(
                to_email=email_responsable,
                subject=f"🔄 Factura {numero_factura} devuelta por contabilidad",
                body_html=html_content
            )

            destinatarios_notificados.append(email_responsable)
            notificaciones_exitosas += 1

            logger.info(
                f"Email de devolución enviado a responsable: {email_responsable}",
                extra={"factura_id": factura_id, "responsable_email": email_responsable}
            )

        except Exception as e:
            logger.error(
                f"Error enviando email a responsable {email_responsable}: {str(e)}",
                exc_info=True,
                extra={"factura_id": factura_id}
            )

    # ========================================================================
    # ACTUALIZAR ESTADO DE FACTURA
    # ========================================================================

    estado_anterior = factura.estado.value

    # Cambiar estado a rechazada (por ahora, luego podemos crear estado "devuelta")
    # TODO: Agregar estado "devuelta" a enum EstadoFactura
    factura.estado = EstadoFactura.rechazada

    # Registrar información de la devolución en campos de rechazo
    factura.rechazado_por = devuelto_por
    factura.fecha_rechazo = datetime.now()
    factura.motivo_rechazo = "DEVUELTA_POR_CONTABILIDAD"

    db.commit()
    db.refresh(factura)

    # Log de auditoría
    logger.info(
        f"Factura devuelta por contabilidad",
        extra={
            "factura_id": factura_id,
            "numero_factura": numero_factura,
            "contador": current_user.usuario,
            "estado_anterior": estado_anterior,
            "estado_nuevo": factura.estado.value,
            "notificaciones_enviadas": notificaciones_exitosas,
            "destinatarios": destinatarios_notificados
        }
    )

    # ========================================================================
    # RETORNAR RESPUESTA
    # ========================================================================

    mensaje = f"Factura devuelta exitosamente."
    if notificaciones_exitosas > 0:
        mensaje += f" Se enviaron {notificaciones_exitosas} notificaciones."
    else:
        mensaje += " No se enviaron notificaciones (emails no configurados)."

    return DevolucionResponse(
        success=True,
        factura_id=factura.id,
        numero_factura=numero_factura,
        estado_anterior=estado_anterior,
        estado_nuevo=factura.estado.value,
        notificaciones_enviadas=notificaciones_exitosas,
        destinatarios=destinatarios_notificados,
        mensaje=mensaje,
        timestamp=datetime.now()
    )


@router.get(
    "/facturas/pendientes",
    summary="Listar facturas pendientes de procesar",
    description="""
    Lista todas las facturas aprobadas pendientes de procesar por contabilidad.

    **Permisos:** Solo usuarios con rol 'contador'
    """
)
async def get_facturas_pendientes(
    current_user=Depends(require_role("contador")),
    db: Session = Depends(get_db)
):
    """
    Endpoint para que contadores vean facturas pendientes de procesar.
    """
    facturas = (
        db.query(Factura)
        .filter(
            Factura.estado.in_([EstadoFactura.aprobada, EstadoFactura.aprobada_auto])
        )
        .order_by(Factura.fecha_emision.desc())
        .all()
    )

    return {
        "total": len(facturas),
        "facturas": [
            {
                "id": f.id,
                "numero_factura": f.numero_factura,
                "proveedor": f.proveedor.razon_social if f.proveedor else None,
                "monto": float(f.total_a_pagar or f.total_calculado or 0),
                "fecha_emision": f.fecha_emision.isoformat() if f.fecha_emision else None,
                "estado": f.estado.value
            }
            for f in facturas
        ]
    }
