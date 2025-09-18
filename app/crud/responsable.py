# app/crud/responsable.py
from sqlalchemy.orm import Session
from app.models.responsable import Responsable, ResponsableNit
from typing import Optional
from app.schemas.responsable import ResponsableCreate, ResponsableNitCreate


def get_responsable_by_id(db: Session, id: int) -> Optional[Responsable]:
    return db.query(Responsable).filter(Responsable.id == id).first()

def get_responsable_by_usuario(db: Session, usuario: str) -> Optional[Responsable]:
    return db.query(Responsable).filter(Responsable.usuario == usuario).first()

def create_responsable(
    db: Session, 
    r: ResponsableCreate) -> Responsable:
    from app.core.security import hash_password
    hashed = hash_password(r.password)
    
    db_obj = Responsable(
        usuario=r.usuario, 
        email=r.email, 
        nombre=r.nombre, 
        hashed_password=hashed, 
        activo=True,
        role_id=r.role_id,
        nit_asignado=getattr(r, 'nit', None)
    )
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


def delete_responsable(db: Session, id: int) -> bool:
    """Elimina un responsable por id. Retorna True si fue eliminado, False si no existe."""
    responsable = get_responsable_by_id(db, id)
    if not responsable:
        return False
    db.delete(responsable)
    db.commit()
    return True

def get_nits_by_responsable(db: Session, responsable_id: int):
    return db.query(ResponsableNit).filter(ResponsableNit.responsable_id == responsable_id).all()

def create_nit_for_responsable(db: Session, responsable_id: int, nit_in: ResponsableNitCreate):
    from fastapi import HTTPException
    existe = db.query(ResponsableNit).filter_by(responsable_id=responsable_id, nit=nit_in.nit).first()
    if existe:
        raise HTTPException(status_code=400, detail="Este NIT ya está asignado a este responsable")
    nit = ResponsableNit(responsable_id=responsable_id, nit=nit_in.nit)
    db.add(nit)
    responsable = db.query(Responsable).filter(Responsable.id == responsable_id).first()
    if responsable:
        responsable.nit_asignado = nit_in.nit
    db.commit()
    db.refresh(nit)
    return nit

def delete_nit(db: Session, nit_id: int) -> bool:
    nit = db.query(ResponsableNit).filter(ResponsableNit.id == nit_id).first()
    if not nit:
        return False
    db.delete(nit)
    db.commit()
    return True
