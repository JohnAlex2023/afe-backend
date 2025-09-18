#app/api/v1/routers/responsables.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.responsable import ResponsableCreate, ResponsableRead
from app.schemas.common import ErrorResponse
from app.crud.responsable import get_responsable_by_usuario, create_responsable
from app.utils.logger import logger

router = APIRouter(tags=["Responsables"])


@router.post(
    "/",
    response_model=ResponsableRead,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
    summary="Crear responsable",
    description="Crea un nuevo usuario responsable en el sistema."
)
def create_responsable_endpoint(
    payload: ResponsableCreate,
    db: Session = Depends(get_db),
):
    if get_responsable_by_usuario(db, payload.usuario):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario ya existe")
    r = create_responsable(db, payload)
    logger.info("Responsable creado", extra={"id": r.id, "usuario": r.usuario})
    return r



@router.get(
    "/",
    response_model=List[ResponsableRead],
    summary="Listar responsables",
    description="Obtiene todos los responsables registrados."
)
def list_responsables(
    db: Session = Depends(get_db),
):
    from app.models.responsable import Responsable
    return db.query(Responsable).all()
