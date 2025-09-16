# app/crud/proveedor.py
from sqlalchemy.orm import Session
from app.models.proveedor import Proveedor
from app.schemas.proveedor import ProveedorBase
from typing import Optional, List

def get_proveedor(db: Session, proveedor_id: int) -> Optional[Proveedor]:
    return db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()

def list_proveedores(db: Session, skip:int=0, limit:int=100) -> List[Proveedor]:
    return db.query(Proveedor).offset(skip).limit(limit).all()

def create_proveedor(db: Session, data: ProveedorBase) -> Proveedor:
    obj = Proveedor(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
