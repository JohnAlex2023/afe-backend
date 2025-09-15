from sqlalchemy.orm import Session
from app.models.cliente import Cliente

# CRUD para Cliente

def get_cliente(db: Session, cliente_id: int):
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()

def get_clientes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Cliente).offset(skip).limit(limit).all()

def create_cliente(db: Session, cliente: dict):
    db_cliente = Cliente(**cliente)
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente
