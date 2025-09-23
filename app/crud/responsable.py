from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import and_

from app.models.factura import Factura
from app.models.proveedor import Proveedor 
from app.models.responsable import Responsable
from app.schemas.responsable import ResponsableUpdate


# -----------------------------------------------------
# Obtener responsable por ID
# -----------------------------------------------------
def get_responsable_by_id(db: Session, responsable_id: int) -> Optional[Responsable]:
    return db.query(Responsable).filter(Responsable.id == responsable_id).first()


# -----------------------------------------------------
# Obtener responsable por usuario
# -----------------------------------------------------
def get_responsable_by_usuario(db: Session, usuario: str) -> Optional[Responsable]:
    return db.query(Responsable).filter(Responsable.usuario == usuario).first()


# -----------------------------------------------------
# Autenticar responsable
# -----------------------------------------------------
def authenticate(db: Session, usuario: str, password: str) -> Optional[Responsable]:
    from app.core.security import verify_password
    responsable = get_responsable_by_usuario(db, usuario)
    if not responsable or not responsable.hashed_password:
        return None
    if not verify_password(password, responsable.hashed_password):
        return None
    return responsable


# -----------------------------------------------------
# Crear responsable
# -----------------------------------------------------
def create_responsable(db: Session, data) -> Responsable:
    from app.core.security import hash_password
    create_data = data.dict()
    
    # Hash the password if provided
    if "password" in create_data and create_data["password"]:
        create_data["hashed_password"] = hash_password(create_data.pop("password"))
    
    obj = Responsable(**create_data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# -----------------------------------------------------
#eliminar responsable

def update_responsable(db: Session, r_id: int, data: ResponsableUpdate) -> Optional[Responsable]:
    from app.core.security import hash_password
    responsable = get_responsable_by_id(db, r_id)
    if not responsable:
        return None

    update_data = data.dict(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        responsable.hashed_password = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(responsable, field, value)

    db.commit()
    db.refresh(responsable)
    return responsable


def delete_responsable(db: Session, r_id: int) -> bool:
    responsable = get_responsable_by_id(db, r_id)
    if not responsable:
        return False
    db.delete(responsable)
    db.commit()
    return True

