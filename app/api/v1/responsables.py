# app/api/v1/responsables.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.responsable import ResponsableCreate, ResponsableRead
from app.crud.responsable import get_responsable_by_usuario, create_responsable
from app.utils.logger import logger

router = APIRouter(prefix="/responsables", tags=["responsables"])

@router.post("/", response_model=ResponsableRead, status_code=status.HTTP_201_CREATED)
def create_responsable_endpoint(payload: ResponsableCreate, db: Session = Depends(get_db)):
    if get_responsable_by_usuario(db, payload.usuario):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario ya existe")
    r = create_responsable(db, payload)
    logger.info("Responsable creado id=%s usuario=%s", r.id, r.usuario)
    return r
