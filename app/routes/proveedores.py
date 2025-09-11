from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.config import get_db
from app.models import Responsable, Proveedor
from app.schemas import (
    ResponsableSchema, ResponsableCreate,
    ProveedorSchema, ProveedorCreate
)

router = APIRouter()


# ================= RESPONSABLES =================

@router.post(
    "/responsables",
    response_model=ResponsableSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear responsable"
)
def crear_responsable(
    responsable: ResponsableCreate,
    db: Session = Depends(get_db)
) -> ResponsableSchema:
    """Crea un nuevo responsable si el email no existe."""
    existing = db.query(Responsable).filter_by(email=responsable.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un responsable con ese email"
        )

    nuevo = Responsable(
        nombre=responsable.nombre,
        email=responsable.email,
        area=responsable.area,
        activo=responsable.activo,
        role_id=responsable.role_id,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return {
        "id": nuevo.id,
        "nombre": nuevo.nombre,
        "email": nuevo.email,
        "area": nuevo.area,
        "activo": nuevo.activo,
        "role_id": nuevo.role_id,
        "role": nuevo.role.nombre if nuevo.role else None,
    }


@router.get(
    "/responsables",
    response_model=list[ResponsableSchema],
    summary="Listar responsables con nombre de rol"
)
def list_responsables(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
) -> list[ResponsableSchema]:
    """
    Devuelve responsables registrados con el nombre del rol (si existe).
    - **skip**: número de registros a omitir  
    - **limit**: número máximo de registros a devolver  
    """
    responsables = db.query(Responsable).offset(skip).limit(limit).all()
    return [
        {
            "id": r.id,
            "nombre": r.nombre,
            "email": r.email,
            "area": r.area,
            "activo": r.activo,
            "role_id": r.role_id,
            "role": r.role.nombre if r.role else None,
        }
        for r in responsables
    ]


# ================= PROVEEDORES =================

@router.post(
    "/proveedores",
    response_model=ProveedorSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Crear proveedor"
)
def crear_proveedor(
    proveedor: ProveedorCreate,
    db: Session = Depends(get_db)
) -> ProveedorSchema:
    """Crea un nuevo proveedor si el NIT no existe."""
    existing = db.query(Proveedor).filter_by(nit=proveedor.nit).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proveedor con este NIT ya existe"
        )

    nuevo = Proveedor(**proveedor.dict(exclude_unset=True))
    db.add(nuevo)

    try:
        db.commit()
        db.refresh(nuevo)
        return nuevo
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear proveedor: {str(e)}"
        )


@router.get(
    "/proveedores/{proveedor_id}",
    response_model=ProveedorSchema,
    summary="Obtener proveedor por ID"
)
def get_proveedor(
    proveedor_id: int,
    db: Session = Depends(get_db)
) -> ProveedorSchema:
    """Devuelve un proveedor por su ID."""
    proveedor = db.query(Proveedor).filter_by(id=proveedor_id).first()
    if not proveedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proveedor no encontrado"
        )
    return proveedor


@router.get(
    "/proveedores",
    response_model=list[ProveedorSchema],
    summary="Listar proveedores con paginación"
)
def list_proveedores(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
) -> list[ProveedorSchema]:
    """
    Devuelve proveedores registrados con paginación.
    - **skip**: número de registros a omitir  
    - **limit**: número máximo de registros a devolver  
    """
    return db.query(Proveedor).offset(skip).limit(limit).all()
