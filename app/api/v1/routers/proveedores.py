from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.schemas.proveedor import ProveedorBase, ProveedorRead
from app.schemas.common import ErrorResponse
from app.crud.proveedor import create_proveedor, list_proveedores, get_proveedor, update_proveedor, delete_proveedor
from app.core.security import get_current_responsable, require_role
from app.utils.logger import logger

router = APIRouter(tags=["Proveedores"])


@router.get(
    "/",
    response_model=List[ProveedorRead],
    summary="Listar proveedores",
    description="Obtiene una lista paginada de proveedores."
)
def list_all(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    return list_proveedores(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=ProveedorRead,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
    summary="Crear proveedor",
    description="Registra un nuevo proveedor en el sistema."
)
def create(
    payload: ProveedorBase,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable")),
):
    p = create_proveedor(db, payload)
    logger.info("Proveedor creado", extra={"id": p.id, "usuario": current_user.usuario})
    return p


@router.get(
    "/{proveedor_id}",
    response_model=ProveedorRead,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener proveedor",
    description="Devuelve los datos de un proveedor específico por ID."
)
def get_one(
    proveedor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    p = get_proveedor(db, proveedor_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    return p


@router.put(
    "/{proveedor_id}",
    response_model=ProveedorRead,
    responses={404: {"model": ErrorResponse}},
    summary="Actualizar proveedor",
    description="Actualiza los datos de un proveedor por su ID."
)
def update(
    proveedor_id: int,
    payload: ProveedorBase,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    p = update_proveedor(db, proveedor_id, payload)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    logger.info("Proveedor actualizado", extra={"id": p.id, "usuario": current_user.usuario})
    return p


@router.delete(
    "/{proveedor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
    summary="Eliminar proveedor",
    description="Elimina un proveedor por su ID."
)
def delete(
    proveedor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    ok = delete_proveedor(db, proveedor_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    logger.info("Proveedor eliminado", extra={"id": proveedor_id, "usuario": current_user.usuario})
    return None
