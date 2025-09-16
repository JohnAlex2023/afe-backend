# app/crud/responsable.py
from sqlalchemy.orm import Session
from app.models.responsable import Responsable
from typing import Optional
from app.schemas.responsable import ResponsableCreate


def get_responsable_by_id(db: Session, id: int) -> Optional[Responsable]:
    return db.query(Responsable).filter(Responsable.id == id).first()

def get_responsable_by_usuario(db: Session, usuario: str) -> Optional[Responsable]:
    return db.query(Responsable).filter(Responsable.usuario == usuario).first()

def create_responsable(db: Session, r: ResponsableCreate) -> Responsable:
    from app.core.security import hash_password
    hashed = hash_password(r.password)
    db_obj = Responsable(usuario=r.usuario, email=r.email, nombre=r.nombre, hashed_password=hashed, activo=True)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def authenticate(db: Session, username: str, password: str) -> Optional[Responsable]:
    from app.core.security import verify_password
    user = get_responsable_by_usuario(db, username)
    if not user or not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
