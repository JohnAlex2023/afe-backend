from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.cliente import ClienteSchema
from app.crud.cliente import get_cliente, get_clientes, create_cliente
from app.db.session import SessionLocal

router = APIRouter(prefix="/clientes", tags=["clientes"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[ClienteSchema])
def listar_clientes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_clientes(db, skip=skip, limit=limit)

@router.get("/{cliente_id}", response_model=ClienteSchema)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = get_cliente(db, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente
