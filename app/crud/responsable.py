from sqlalchemy.orm import Session
from app.models.responsable import Responsable

# CRUD para Responsable

def get_responsable(db: Session, responsable_id: int):
    return db.query(Responsable).filter(Responsable.id == responsable_id).first()

def get_responsables(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Responsable).offset(skip).limit(limit).all()

def create_responsable(db: Session, responsable: dict):
    db_responsable = Responsable(**responsable)
    db.add(db_responsable)
    db.commit()
    db.refresh(db_responsable)
    return db_responsable
