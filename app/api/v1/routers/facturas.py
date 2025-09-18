# app/api/v1/routers/facturas.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.schemas.factura import FacturaCreate, FacturaRead
from app.schemas.common import ErrorResponse
from app.services.invoice_service import process_and_persist_invoice
from app.core.security import get_current_responsable, require_role
from app.crud.factura import (
    list_facturas,
    get_factura,
    find_by_cufe,
    get_factura_by_numero,
)
from app.utils.logger import logger


router = APIRouter(tags=["Facturas"])


# -----------------------------------------------------
# Listar todas las facturas (con filtros opcionales)
# -----------------------------------------------------
@router.get(
    "/",
    response_model=List[FacturaRead],
    summary="Listar facturas",
    description="Obtiene una lista paginada de facturas. Se puede filtrar por NIT o número de factura."
)
def list_all(
    skip: int = 0,
    limit: int = 100,
    nit: Optional[str] = None,
    numero_factura: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    return list_facturas(
        db,
        skip=skip,
        limit=limit,
        nit=nit,
        numero_factura=numero_factura
    )


# -----------------------------------------------------
# Crear o actualizar factura
# -----------------------------------------------------
@router.post(
    "/",
    response_model=FacturaRead,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
    summary="Crear o actualizar factura",
    description="Procesa una nueva factura. Si ya existe, devuelve un error de conflicto."
)
def create_invoice(
    payload: FacturaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable")),
):
    result, action = process_and_persist_invoice(
        db, payload, created_by=current_user.usuario
    )

    if action == "conflict":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflicto con factura existente"
        )

    f = get_factura(db, result["id"])
    logger.info(
        "Factura procesada",
        extra={"id": f.id, "usuario": current_user.usuario, "action": action}
    )
    return f


# -----------------------------------------------------
# Obtener factura por ID
# -----------------------------------------------------
@router.get(
    "/{factura_id}",
    response_model=FacturaRead,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener factura por ID",
    description="Devuelve los datos de una factura específica por ID."
)
def get_one(
    factura_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    f = get_factura(db, factura_id)
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )
    return f


# -----------------------------------------------------
# Obtener facturas por NIT
# -----------------------------------------------------
@router.get(
    "/nit/{nit}",
    response_model=List[FacturaRead],
    summary="Listar facturas por NIT",
    description="Obtiene todas las facturas asociadas a un proveedor por NIT."
)
def get_by_nit(
    nit: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    return list_facturas(db, skip=skip, limit=limit, nit=nit)


# -----------------------------------------------------
# Obtener factura por CUFE
# -----------------------------------------------------
@router.get(
    "/cufe/{cufe}",
    response_model=FacturaRead,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener factura por CUFE",
    description="Devuelve una factura única usando el CUFE."
)
def get_by_cufe(
    cufe: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    f = find_by_cufe(db, cufe)
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )
    return f


# -----------------------------------------------------
# Obtener factura por número de factura
# -----------------------------------------------------
@router.get(
    "/numero/{numero_factura}",
    response_model=FacturaRead,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener factura por número de factura",
    description="Devuelve una factura única usando el número de factura."
)
def get_by_numero(
    numero_factura: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    f = get_factura_by_numero(db, numero_factura)
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )
    return f
