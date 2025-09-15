from app.models.cliente import Cliente
from sqlalchemy.orm import Session

# Ejemplo de lógica de negocio para clientes

def cliente_existe(db: Session, nit: str) -> bool:
    return db.query(Cliente).filter(Cliente.nit == nit).first() is not None

# Puedes agregar aquí más lógica de negocio específica de clientes
