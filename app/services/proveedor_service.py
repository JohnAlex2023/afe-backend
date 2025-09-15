from app.models.proveedor import Proveedor
from sqlalchemy.orm import Session

# Ejemplo de lógica de negocio para proveedores

def proveedor_existe(db: Session, nit: str) -> bool:
    return db.query(Proveedor).filter(Proveedor.nit == nit).first() is not None

# Puedes agregar aquí más lógica de negocio específica de proveedores
