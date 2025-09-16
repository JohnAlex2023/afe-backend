# app/api/v1/proveedores.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas.proveedor import ProveedorBase, ProveedorRead
from app.crud.proveedor import create_proveedor, list_proveedores, get_proveedor
from app.core.security import get_current_responsable

router = APIRouter(prefix="/proveedores", tags=["proveedores"])

@router.get("/", response_model=List[ProveedorRead])
def list_all(skip:int=0, limit:int=100, db: Session = Depends(get_db), current_user = Depends(get_current_responsable)):
    return list_proveedores(db, skip=skip, limit=limit)

@router.post("/", response_model=ProveedorRead, status_code=status.HTTP_201_CREATED)
def create(payload: ProveedorBase, db: Session = Depends(get_db), current_user = Depends(get_current_responsable)):
    return create_proveedor(db, payload)

@router.get("/{proveedor_id}", response_model=ProveedorRead)
def get_one(proveedor_id:int, db: Session = Depends(get_db), current_user = Depends(get_current_responsable)):
    p = get_proveedor(db, proveedor_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    return p
