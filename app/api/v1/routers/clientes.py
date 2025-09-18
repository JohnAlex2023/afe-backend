from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.schemas.cliente import ClienteBase, ClienteRead
from app.schemas.common import ErrorResponse
from app.crud.cliente import create_cliente, list_clientes, get_cliente
from app.core.security import get_current_responsable, require_role
from app.utils.logger import logger

router = APIRouter(tags=["Clientes"])


@router.get(
    "/",
    response_model=List[ClienteRead],
    summary="Listar clientes",
    description="Obtiene una lista paginada de clientes registrados en el sistema.",
)
def list_all(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable")),
):
    return list_clientes(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=ClienteRead,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
    summary="Crear cliente",
    description="Registra un nuevo cliente en el sistema."
)
def create(
    payload: ClienteBase,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable")),
):
    c = create_cliente(db, payload)
    logger.info("Cliente creado", extra={"id": c.id, "usuario": current_user.usuario})
    return c


@router.get(
    "/{cliente_id}",
    response_model=ClienteRead,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener cliente",
    description="Devuelve los datos de un cliente específico."
)
def get_one(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    c = get_cliente(db, cliente_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return c
