from sqlalchemy.orm import Session
from app.models.role import Role

# CRUD para Role

def get_role(db: Session, role_id: int):
    return db.query(Role).filter(Role.id == role_id).first()

def get_roles(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Role).offset(skip).limit(limit).all()

def create_role(db: Session, role: dict):
    db_role = Role(**role)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role
