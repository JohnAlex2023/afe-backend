# app/crud/proveedor.py
from sqlalchemy.orm import Session
from app.models.proveedor import Proveedor
from app.schemas.proveedor import ProveedorBase
from app.utils.normalizacion import normalizar_nit, normalizar_email, normalizar_razon_social
from typing import Optional, List

def get_proveedor(db: Session, proveedor_id: int) -> Optional[Proveedor]:
    return db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()

def list_proveedores(db: Session, skip:int=0, limit:int=100) -> List[Proveedor]:
    return db.query(Proveedor).offset(skip).limit(limit).all()

def create_proveedor(db: Session, data: ProveedorBase) -> Proveedor:
    # Normalizar datos antes de crear
    data_dict = data.dict()
    if 'nit' in data_dict and data_dict['nit']:
        data_dict['nit'] = normalizar_nit(data_dict['nit'])
    if 'contacto_email' in data_dict and data_dict['contacto_email']:
        data_dict['contacto_email'] = normalizar_email(data_dict['contacto_email'])
    if 'razon_social' in data_dict and data_dict['razon_social']:
        data_dict['razon_social'] = normalizar_razon_social(data_dict['razon_social'])

    obj = Proveedor(**data_dict)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def update_proveedor(db: Session, proveedor_id: int, data: ProveedorBase) -> Optional[Proveedor]:
    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not proveedor:
        return None

    # Normalizar datos antes de actualizar
    data_dict = data.dict(exclude_unset=True)
    if 'nit' in data_dict and data_dict['nit']:
        data_dict['nit'] = normalizar_nit(data_dict['nit'])
    if 'contacto_email' in data_dict and data_dict['contacto_email']:
        data_dict['contacto_email'] = normalizar_email(data_dict['contacto_email'])
    if 'razon_social' in data_dict and data_dict['razon_social']:
        data_dict['razon_social'] = normalizar_razon_social(data_dict['razon_social'])

    for key, value in data_dict.items():
        setattr(proveedor, key, value)
    db.commit()
    db.refresh(proveedor)
    return proveedor

def delete_proveedor(db: Session, proveedor_id: int) -> bool:
    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not proveedor:
        return False
    db.delete(proveedor)
    db.commit()
    return True
