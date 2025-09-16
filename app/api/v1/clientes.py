# app/api/v1/clientes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas.cliente import ClienteBase, ClienteRead
from app.crud.cliente import create_cliente, list_clientes, get_cliente
from app.core.security import get_current_responsable

router = APIRouter(prefix="/clientes", tags=["clientes"])

@router.get("/", response_model=List[ClienteRead])
def list_all(skip:int=0, limit:int=100, db: Session = Depends(get_db), current_user = Depends(get_current_responsable)):
    return list_clientes(db, skip=skip, limit=limit)

@router.post("/", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
def create(payload: ClienteBase, db: Session = Depends(get_db), current_user = Depends(get_current_responsable)):
    return create_cliente(db, payload)

@router.get("/{cliente_id}", response_model=ClienteRead)
def get_one(cliente_id:int, db: Session = Depends(get_db), current_user = Depends(get_current_responsable)):
    c = get_cliente(db, cliente_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return c
