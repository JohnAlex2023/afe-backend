from sqlalchemy.orm import Session
from app.models.proveedor import Proveedor

# CRUD para Proveedor

def get_proveedor(db: Session, proveedor_id: int):
    return db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()

def get_proveedores(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Proveedor).offset(skip).limit(limit).all()

def create_proveedor(db: Session, proveedor: dict):
    db_proveedor = Proveedor(**proveedor)
    db.add(db_proveedor)
    db.commit()
    db.refresh(db_proveedor)
    return db_proveedor
