from app.models.responsable import Responsable
from sqlalchemy.orm import Session

# Ejemplo de lógica de negocio para responsables

def responsable_por_email(db: Session, email: str):
    return db.query(Responsable).filter(Responsable.email == email).first()

# Puedes agregar aquí más lógica de negocio específica de responsables
