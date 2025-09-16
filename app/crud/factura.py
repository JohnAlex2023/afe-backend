# app/crud/factura.py
from sqlalchemy.orm import Session
from app.models.factura import Factura
from typing import List, Optional
from sqlalchemy import and_

def get_factura(db: Session, factura_id: int) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.id == factura_id).first()

def list_facturas(db: Session, skip:int=0, limit:int=100) -> List[Factura]:
    return db.query(Factura).offset(skip).limit(limit).all()

def find_by_cufe(db: Session, cufe: str) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.cufe == cufe).first()

def find_by_numero_proveedor(db: Session, numero: str, proveedor_id: int) -> Optional[Factura]:
    return db.query(Factura).filter(and_(Factura.numero_factura == numero, Factura.proveedor_id == proveedor_id)).first()

def create_factura(db: Session, data: dict) -> Factura:
    obj = Factura(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def update_factura(db: Session, factura: Factura, fields: dict) -> Factura:
    for k,v in fields.items():
        setattr(factura, k, v)
    db.add(factura)
    db.commit()
    db.refresh(factura)
    return factura
