from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.proveedor import ProveedorSchema
from app.crud.proveedor import get_proveedor, get_proveedores, create_proveedor
from app.db.session import SessionLocal

router = APIRouter(prefix="/proveedores", tags=["proveedores"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[ProveedorSchema])
def listar_proveedores(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_proveedores(db, skip=skip, limit=limit)

@router.get("/{proveedor_id}", response_model=ProveedorSchema)
def obtener_proveedor(proveedor_id: int, db: Session = Depends(get_db)):
    proveedor = get_proveedor(db, proveedor_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor
