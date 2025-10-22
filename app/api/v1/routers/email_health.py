# app/api/v1/routers/email_health.py
"""
Endpoint de health check para servicios de email.

Permite monitorear el estado de Microsoft Graph y SMTP en tiempo real.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.usuario import Usuario
from app.core.dependencies import get_current_user
from app.services.unified_email_service import get_unified_email_service
from app.utils.logger import logger

router = APIRouter()


@router.get("/email/health")
async def email_health_status(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verifica el estado de los servicios de email.

    Solo accesible para administradores.

    Returns:
        Estadísticas de los servicios de email disponibles.
    """
    # Validar que sea admin
    if current_user.rol.nombre != "Admin":
        raise HTTPException(status_code=403, detail="Solo admins")

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
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reinicializa los servicios de email.

    Útil si hay cambios en las variables de entorno o para
    recuperarse de fallos anteriores.

    Solo accesible para administradores.
    """
    # Validar que sea admin
    if current_user.rol.nombre != "Admin":
        raise HTTPException(status_code=403, detail="Solo admins")

    try:
        service = get_unified_email_service()
        service.reinitialize()

        logger.info(
            f"Email services reinicializados por {current_user.usuario}"
        )

        return {
            "status": "success",
            "message": "Email services reinicializados",
            "active_provider": service.get_active_provider()
        }
    except Exception as e:
        logger.error(f"Error reinicializando servicios: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )
