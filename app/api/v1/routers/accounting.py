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
from app.schemas.factura import FacturaRead
from app.schemas.common import ErrorResponse
from app.models.factura import Factura, EstadoFactura
from app.models.workflow_aprobacion import WorkflowAprobacionFactura
from app.services.unified_email_service import UnifiedEmailService
from app.services.email_template_service import EmailTemplateService
from app.utils.logger import logger
from pydantic import BaseModel, Field
from typing import Optional


router = APIRouter(tags=["Contabilidad"])


# =====================================================================
# SCHEMAS INLINE - Validación de Facturas por Contador
# =====================================================================

class ValidacionRequest(BaseModel):
    """Request para validar una factura por Contador"""
    observaciones: Optional[str] = Field(
        None,
        max_length=500,
        description="Observaciones opcionales sobre la validación"
    )


class ValidacionResponse(BaseModel):
    """Response después de validar una factura"""
    success: bool
    factura_id: int
    numero_factura: str
    estado_anterior: str
    estado_nuevo: str
    validado_por: str
    fecha_validacion: datetime
    observaciones: Optional[str] = None
    mensaje: str


# =====================================================================
# ENDPOINT: Obtener facturas por revisar (Contador)
# =====================================================================

@router.get(
    "/facturas/por-revisar",
    response_model=dict,
    summary="Obtener facturas pendientes de validación",
    description="""
    Contador obtiene todas las facturas que necesita validar.

    **Permisos:** Solo usuarios con rol 'contador' pueden ejecutar.

    **Retorna:**
    - Facturas en estado 'aprobada' o 'aprobada_auto'
    - Información para tomar decisión de validación
    - Estadísticas de pendientes
    """
)
async def obtener_facturas_por_revisar(
    current_user=Depends(require_role("contador")),
    db: Session = Depends(get_db),
    solo_pendientes: bool = True,
    pagina: int = 1,
    limit: int = 50
):
    """Obtener facturas pendientes de validación por Contador"""

    # Query base: facturas aprobadas
    query = db.query(Factura).filter(
        Factura.estado.in_([EstadoFactura.aprobada, EstadoFactura.aprobada_auto])
    )

    # Opcional: si quiere ver SOLO las no validadas aún
    if solo_pendientes:
        # (en realidad esto es redundante porque la query ya filtra aprobadas)
        pass

    # Ordenar por fecha más reciente
    query = query.order_by(Factura.creado_en.desc())

    # Paginación
    total = query.count()
    skip = (pagina - 1) * limit
    facturas = query.offset(skip).limit(limit).all()

    # Convertir a schema
    facturas_data = [FacturaRead.model_validate(f) for f in facturas]

    # Estadísticas
    estadisticas = {
        "total_pendiente": total,
        "monto_pendiente": sum(
            float(f.total_a_pagar or 0) for f in facturas
        ),
        "validadas_hoy": db.query(Factura).filter(
            Factura.estado == EstadoFactura.validada_contabilidad,
            Factura.actualizado_en >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
    }

    logger.info(
        "Contador consultó facturas por revisar: %s facturas, página %s",
        len(facturas),
        pagina,
        extra={"contador": current_user.usuario}
    )

    return {
        "facturas": facturas_data,
        "paginacion": {
            "pagina": pagina,
            "limit": limit,
            "total": total
        },
        "estadisticas": estadisticas
    }


# =====================================================================
# ENDPOINT: Validar factura (Contador aprueba para Tesorería)
# =====================================================================

@router.post(
    "/facturas/{factura_id}/validar",
    response_model=ValidacionResponse,
    summary="Validar factura - Contador aprueba",
    description="""
    Contador valida que la factura sea correcta y está lista para Tesorería.

    **Permisos:** Solo usuarios con rol 'contador' pueden ejecutar.

    **Condiciones:**
    - Factura debe estar en estado 'aprobada' o 'aprobada_auto'
    - Cambiar estado a 'validada_contabilidad'

    **Nota:** Tesorería es sistema aparte. Solo enviamos facturas validadas.
    """
)
async def validar_factura(
    factura_id: int,
    request: ValidacionRequest,
    current_user=Depends(require_role("contador")),
    db: Session = Depends(get_db)
):
    """Validar factura por Contador - sin emails"""

    # Obtener factura
    factura = db.query(Factura).filter(Factura.id == factura_id).first()

    if not factura:
        logger.warning(
            "Intento de validar factura inexistente: %s por %s",
            factura_id,
            current_user.usuario
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Factura con ID {factura_id} no encontrada"
        )

    # Validar que esté aprobada
    if factura.estado not in [EstadoFactura.aprobada, EstadoFactura.aprobada_auto]:
        logger.warning(
            "Intento de validar factura en estado inválido: %s (factura_id: %s)",
            factura.estado.value,
            factura_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo puedes validar facturas aprobadas. Esta está: {factura.estado.value}"
        )

    # Cambiar estado
    estado_anterior = factura.estado.value
    factura.estado = EstadoFactura.validada_contabilidad
    db.commit()
    db.refresh(factura)

    # Log de auditoría
    logger.info(
        "Factura validada por contador: %s (ID: %s)",
        factura.numero_factura,
        factura_id,
        extra={
            "contador": current_user.usuario,
            "estado_anterior": estado_anterior,
            "estado_nuevo": factura.estado.value,
            "observaciones": request.observaciones
        }
    )

    # Retornar respuesta
    validado_por = current_user.nombre if hasattr(current_user, 'nombre') else current_user.usuario

    return ValidacionResponse(
        success=True,
        factura_id=factura.id,
        numero_factura=factura.numero_factura,
        estado_anterior=estado_anterior,
        estado_nuevo=factura.estado.value,
        validado_por=validado_por,
        fecha_validacion=datetime.now(),
        observaciones=request.observaciones,
        mensaje="Factura validada exitosamente. Lista para Tesorería."
    )


# =====================================================================
# ENDPOINT: Devolver factura (Contador requiere corrección)
# =====================================================================

@router.post(
    "/facturas/{factura_id}/devolver",
    response_model=DevolucionResponse,
    summary="Devolver factura al proveedor",
    description="""
    Devuelve una factura al proveedor solicitando información adicional.

    **Permisos:** SOLO usuarios con rol 'contador' pueden ejecutar esta acción.
    Admin tiene acceso de lectura (historial, pendientes) pero NO puede devolver facturas.

    **Flujo:**
    1. Contador encuentra que una factura aprobada necesita información adicional
    2. Usa este endpoint especificando qué información falta
    3. Sistema envía emails a:
       - Proveedor (solicitando la información)
       - Usuario que aprobó (notificación informativa)
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
            "description": "Sin permisos (solo contador puede devolver facturas)"
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

    # Email del usuario que aprobó
    email_responsable = None
    nombre_responsable = "Usuario"
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

    # Enviar email al usuario (si usuario lo solicita)
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

    # Cambiar estado a devuelta_contabilidad (nuevo estado para Contador)
    factura.estado = EstadoFactura.devuelta_contabilidad

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


