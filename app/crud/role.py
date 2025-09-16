# app/crud/role.py
from sqlalchemy.orm import Session
from app.models.role import Role
from typing import List, Optional

def get_role(db: Session, role_id: int) -> Optional[Role]:
    return db.query(Role).filter(Role.id == role_id).first()

def get_role_by_name(db: Session, nombre: str) -> Optional[Role]:
    return db.query(Role).filter(Role.nombre == nombre).first()

def list_roles(db: Session, skip:int=0, limit:int=100) -> List[Role]:
    return db.query(Role).offset(skip).limit(limit).all()

