from app.models.role import Role
from sqlalchemy.orm import Session

# Ejemplo de lógica de negocio para roles

def obtener_role_por_nombre(db: Session, nombre: str):
    return db.query(Role).filter(Role.nombre == nombre).first()

# Puedes agregar aquí más lógica de negocio específica de roles
