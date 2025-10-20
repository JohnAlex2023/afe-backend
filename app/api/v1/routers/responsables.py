#app/api/v1/routers/responsables.py
"""
Router para gestión de Responsables.

⚠️ IMPORTANTE: Algunos endpoints relacionados con responsable-proveedor
fueron movidos a /api/v1/asignacion-nit/*

✅ NUEVOS ENDPOINTS: Ver /api/v1/asignacion-nit/
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.responsable import ResponsableCreate, ResponsableRead, ResponsableUpdate
from app.schemas.common import ErrorResponse
from app.crud.responsable import (
    get_responsable_by_usuario,
    create_responsable,
    update_responsable,
    delete_responsable
)
from app.core.security import get_current_responsable, require_role
from app.utils.logger import logger

router = APIRouter(tags=["Responsables"])


# ==================== ENDPOINTS DE RESPONSABLES ====================

@router.post(
    "/",
    response_model=ResponsableRead,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
    summary="Crear responsable",
    description="Crea un nuevo usuario responsable en el sistema."
)
def create_responsable_endpoint(
    payload: ResponsableCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Crea un nuevo responsable"""
    if get_responsable_by_usuario(db, payload.usuario):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario ya existe"
        )

    r = create_responsable(db, payload)
    logger.info("Responsable creado", extra={"id": r.id, "usuario": r.usuario})
    return r


@router.get(
    "/",
    response_model=List[ResponsableRead],
    summary="Listar responsables",
    description="Obtiene todos los responsables registrados."
)
def list_responsables(
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable")),
):
    """Lista todos los responsables"""
    from app.models.responsable import Responsable
    return db.query(Responsable).all()


@router.get(
    "/{responsable_id}",
    response_model=ResponsableRead,
    summary="Obtener responsable por ID",
    description="Obtiene un responsable específico por su ID."
)
def get_responsable(
    responsable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable")),
):
    """Obtiene un responsable por ID"""
    from app.models.responsable import Responsable

    responsable = db.query(Responsable).filter(Responsable.id == responsable_id).first()

    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable con ID {responsable_id} no encontrado"
        )

    return responsable


@router.put(
    "/{responsable_id}",
    response_model=ResponsableRead,
    summary="Actualizar responsable",
    description="Actualiza la información de un responsable."
)
def update_responsable_endpoint(
    responsable_id: int,
    payload: ResponsableUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Actualiza un responsable"""
    responsable = update_responsable(db, responsable_id, payload)

    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable con ID {responsable_id} no encontrado"
        )

    logger.info(f"Responsable actualizado: {responsable_id}")
    return responsable


@router.delete(
    "/{responsable_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar responsable",
    description="Elimina (desactiva) un responsable del sistema."
)
def delete_responsable_endpoint(
    responsable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Elimina (desactiva) un responsable"""
    success = delete_responsable(db, responsable_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable con ID {responsable_id} no encontrado"
        )

    logger.info(f"Responsable eliminado: {responsable_id}")
    return None


# ==================== ENDPOINTS DE ASIGNACIONES ====================
# ⚠️ NOTA: Los endpoints de asignación responsable-proveedor fueron
# movidos a /api/v1/asignacion-nit/*
#
# - GET /asignacion-nit/ - Listar asignaciones
# - POST /asignacion-nit/ - Crear asignación
# - PUT /asignacion-nit/{id} - Actualizar asignación
# - DELETE /asignacion-nit/{id} - Eliminar asignación
# - POST /asignacion-nit/bulk - Asignación masiva
# - GET /asignacion-nit/por-responsable/{responsable_id} - Asignaciones por responsable
#
# ==================== FIN DEL ARCHIVO ====================
