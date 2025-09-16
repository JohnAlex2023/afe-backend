# app/crud/cliente.py
from sqlalchemy.orm import Session
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteBase
from typing import Optional, List

def get_cliente(db: Session, cliente_id: int) -> Optional[Cliente]:
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()

def list_clientes(db: Session, skip:int=0, limit:int=100) -> List[Cliente]:
    return db.query(Cliente).offset(skip).limit(limit).all()

def create_cliente(db: Session, data: ClienteBase) -> Cliente:
    obj = Cliente(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
