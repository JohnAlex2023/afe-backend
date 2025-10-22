# app/api/v1/routers/email_health.py
"""
Endpoint de health check para servicios de email.

Permite monitorear el estado de Microsoft Graph y SMTP en tiempo real.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_role
from app.services.unified_email_service import get_unified_email_service
from app.utils.logger import logger

router = APIRouter()


@router.get("/email/health")
async def email_health_status(
    current_user = Depends(require_role("admin"))
):
    """
    Verifica el estado de los servicios de email.

    Solo accesible para administradores.

    Returns:
        Estadísticas de los servicios de email disponibles.
    """
    # El decorador require_role ya valida que sea admin

    service = get_unified_email_service()

    return {
        "status": "ok",
        "graph_service": {
            "configured": bool(service.graph_service),
            "available": service.graph_service is not None
        },
        "smtp_service": {
            "configured": bool(service.smtp_service),
            "available": service.smtp_service is not None
        },
        "active_provider": service.get_active_provider(),
        "message": (
            "Email services operational"
            if service.get_active_provider() != "none"
            else "WARNING: No email services available"
        )
    }


@router.post("/email/reinitialize")
async def reinitialize_email_services(
    current_user = Depends(require_role("admin"))
):
    """
    Reinicializa los servicios de email.

    Útil si hay cambios en las variables de entorno o para
    recuperarse de fallos anteriores.

    Solo accesible para administradores.
    """
    # El decorador require_role ya valida que sea admin

    try:
        service = get_unified_email_service()
        service.reinitialize()

        logger.info("Email services reinicializados por admin")

        return {
            "status": "success",
            "message": "Email services reinicializados",
            "active_provider": service.get_active_provider()
        }
    except Exception as e:
        logger.error("Error reinicializando servicios: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        ) from e
