from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.factura import FacturaSchema
from app.crud.factura import get_factura, get_facturas, create_factura
from app.db.session import SessionLocal

router = APIRouter(prefix="/facturas", tags=["facturas"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[FacturaSchema])
def listar_facturas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_facturas(db, skip=skip, limit=limit)

@router.get("/{factura_id}", response_model=FacturaSchema)
def obtener_factura(factura_id: int, db: Session = Depends(get_db)):
    factura = get_factura(db, factura_id)
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return factura
