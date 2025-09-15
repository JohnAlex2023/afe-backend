from sqlalchemy.orm import Session
from app.models.factura import Factura

# CRUD para Factura

def get_factura(db: Session, factura_id: int):
    return db.query(Factura).filter(Factura.id == factura_id).first()

def get_facturas(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Factura).offset(skip).limit(limit).all()

def create_factura(db: Session, factura: dict):
    db_factura = Factura(**factura)
    db.add(db_factura)
    db.commit()
    db.refresh(db_factura)
    return db_factura
