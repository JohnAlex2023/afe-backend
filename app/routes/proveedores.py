# app/routers/responsables_proveedores.py

from typing import List, Any, Dict
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.config import get_db
from app.models import Responsable, Proveedor
from app.schemas import (
    ResponsableSchema, ResponsableCreate,
    ProveedorSchema, ProveedorCreate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# -------------------------
# Helpers
# -------------------------
def get_or_404(db: Session, model, **filters) -> Any:
    """
    Busca un registro según filtros o lanza un HTTP 404 si no existe.
    """
    instance = db.query(model).filter_by(**filters).first()
    if not instance:
        logger.warning("%s no encontrado. Filtros: %s", model.__name__, filters)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} no encontrado",
        )
    return instance


# -------------------------
# RESPONSABLES
# -------------------------
@router.post(
    "/responsables",
    response_model=ResponsableSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear responsable",
)
def crear_responsable(
    responsable: ResponsableCreate,
    db: Session = Depends(get_db),
) -> ResponsableSchema:
    """
    Crea un nuevo responsable.
    Valida que no exista previamente con el mismo email.
    """
    if db.query(Responsable).filter_by(email=responsable.email).first():
        logger.info("Intento de duplicado al crear responsable con email=%s", responsable.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un responsable con ese email",
        )

    nuevo = Responsable(**responsable.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    logger.info("Responsable creado exitosamente con id=%s", nuevo.id)
    return nuevo


@router.get(
    "/responsables",
    response_model=List[ResponsableSchema],
    summary="Listar responsables",
)
def listar_responsables(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
) -> List[ResponsableSchema]:
    """
    Lista responsables con paginación (skip, limit).
    """
    responsables = db.query(Responsable).offset(skip).limit(limit).all()
    logger.info("Se listaron %s responsables (skip=%s, limit=%s)", len(responsables), skip, limit)
    return responsables


# -------------------------
# PROVEEDORES
# -------------------------
@router.post(
    "/proveedores",
    response_model=ProveedorSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear proveedor",
)
def crear_proveedor(
    proveedor: ProveedorCreate,
    db: Session = Depends(get_db),
) -> ProveedorSchema:
    """
    Crea un nuevo proveedor.
    Valida duplicados por NIT y maneja errores de integridad.
    """
    if db.query(Proveedor).filter_by(nit=proveedor.nit).first():
        logger.info("Intento de duplicado al crear proveedor con NIT=%s", proveedor.nit)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proveedor con este NIT ya existe",
        )

    nuevo = Proveedor(**proveedor.model_dump())
    try:
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        logger.info("Proveedor creado exitosamente con id=%s", nuevo.id)
        return nuevo
    except IntegrityError as e:
        db.rollback()
        logger.error("Error al crear proveedor: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear proveedor",
        )


@router.get(
    "/proveedores/{proveedor_id}",
    response_model=ProveedorSchema,
    summary="Obtener proveedor por ID",
)
def obtener_proveedor(
    proveedor_id: int,
    db: Session = Depends(get_db),
) -> ProveedorSchema:
    """
    Obtiene un proveedor específico por su ID.
    """
    proveedor = get_or_404(db, Proveedor, id=proveedor_id)
    logger.info("Proveedor recuperado con id=%s", proveedor.id)
    return proveedor


@router.get(
    "/proveedores",
    response_model=List[ProveedorSchema],
    summary="Listar proveedores",
)
def listar_proveedores(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
) -> List[ProveedorSchema]:
    """
    Lista proveedores con paginación (skip, limit).
    """
    proveedores = db.query(Proveedor).offset(skip).limit(limit).all()
    logger.info("Se listaron %s proveedores (skip=%s, limit=%s)", len(proveedores), skip, limit)
    return proveedores
