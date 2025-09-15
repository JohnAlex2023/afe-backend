from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.responsable import ResponsableSchema
from app.crud.responsable import get_responsable, get_responsables, create_responsable
from app.db.session import SessionLocal

router = APIRouter(prefix="/responsables", tags=["responsables"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[ResponsableSchema])
def listar_responsables(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_responsables(db, skip=skip, limit=limit)

@router.get("/{responsable_id}", response_model=ResponsableSchema)
def obtener_responsable(responsable_id: int, db: Session = Depends(get_db)):
    responsable = get_responsable(db, responsable_id)
    if not responsable:
        raise HTTPException(status_code=404, detail="Responsable no encontrado")
    return responsable
