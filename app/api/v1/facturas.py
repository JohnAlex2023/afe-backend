# app/api/v1/facturas.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas.factura import FacturaCreate, FacturaRead
from app.services.invoice_service import process_and_persist_invoice
from app.core.security import get_current_responsable
from app.crud.factura import list_facturas, get_factura

router = APIRouter(prefix="/facturas", tags=["facturas"])

@router.get("/", response_model=List[FacturaRead])
def list_all(skip:int=0, limit:int=100, db: Session = Depends(get_db), current_user = Depends(get_current_responsable)):
    return list_facturas(db, skip=skip, limit=limit)

@router.post("/", response_model=FacturaRead, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: FacturaCreate, db: Session = Depends(get_db), current_user = Depends(get_current_responsable)):
    result, action = process_and_persist_invoice(db, payload, created_by=current_user.usuario)
    if action == "conflict":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflicto con factura existente")
    # devolver la factura creada/actualizada
    f = get_factura(db, result["id"])
    return f

@router.get("/{factura_id}", response_model=FacturaRead)
def get_one(factura_id:int, db: Session = Depends(get_db), current_user = Depends(get_current_responsable)):
    f = get_factura(db, factura_id)
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")
    return f
