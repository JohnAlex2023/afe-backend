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
# Obtener factura por ID
# -----------------------------------------------------
def get_factura(db: Session, factura_id: int) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.id == factura_id).first()


# -----------------------------------------------------
# Listar facturas (con filtros opcionales)
# -----------------------------------------------------
def list_facturas(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    nit: Optional[str] = None,
    numero_factura: Optional[str] = None,
) -> List[Factura]:
    query = db.query(Factura)

    if nit:
        # Hacemos JOIN con Proveedor y filtramos por NIT
        query = query.join(Proveedor).filter(Proveedor.nit == nit)

    if numero_factura:
        query = query.filter(Factura.numero_factura == numero_factura)

    return query.offset(skip).limit(limit).all()


# -----------------------------------------------------
# Buscar por CUFE
# -----------------------------------------------------
def find_by_cufe(db: Session, cufe: str) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.cufe == cufe).first()


# -----------------------------------------------------
# Buscar por número de factura
# -----------------------------------------------------
def get_factura_by_numero(db: Session, numero_factura: str) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.numero_factura == numero_factura).first()


# -----------------------------------------------------
# Buscar por número de factura y proveedor
# -----------------------------------------------------
def find_by_numero_proveedor(db: Session, numero: str, proveedor_id: int) -> Optional[Factura]:
    return (
        db.query(Factura)
        .filter(
            and_(
                Factura.numero_factura == numero,
                Factura.proveedor_id == proveedor_id
            )
        )
        .first()
    )


# -----------------------------------------------------
# Crear factura
# -----------------------------------------------------
def create_factura(db: Session, data: dict) -> Factura:
    obj = Factura(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# -----------------------------------------------------
# Actualizar factura
# -----------------------------------------------------
def update_factura(db: Session, factura: Factura, fields: dict) -> Factura:
    for k, v in fields.items():
        setattr(factura, k, v)
    db.add(factura)
    db.commit()
    db.refresh(factura)
    return factura


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

