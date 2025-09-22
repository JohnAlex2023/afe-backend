from sqlalchemy.orm import Session
from app.models.responsable_proveedor import ResponsableProveedor
from app.models.proveedor import Proveedor
from typing import List, Optional

# Obtener todos los proveedores asignados a un responsable

def get_proveedores_by_responsable(db: Session, responsable_id: int) -> List[ResponsableProveedor]:
    return db.query(ResponsableProveedor).filter_by(responsable_id=responsable_id, activo=True).all()

# Obtener todos los responsables asignados a un proveedor

def get_responsables_by_proveedor(db: Session, proveedor_id: int) -> List[ResponsableProveedor]:
    return db.query(ResponsableProveedor).filter_by(proveedor_id=proveedor_id, activo=True).all()

# Desactivar una relación responsable-proveedor

def desactivar_responsable_proveedor(db: Session, responsable_id: int, proveedor_id: int) -> bool:
    rel = db.query(ResponsableProveedor).filter_by(responsable_id=responsable_id, proveedor_id=proveedor_id).first()
    if rel:
        rel.activo = False
        db.commit()
        return True
    return False

# Consultar si una relación está activa

def is_responsable_proveedor_activo(db: Session, responsable_id: int, proveedor_id: int) -> bool:
    rel = db.query(ResponsableProveedor).filter_by(responsable_id=responsable_id, proveedor_id=proveedor_id, activo=True).first()
    return rel is not None
