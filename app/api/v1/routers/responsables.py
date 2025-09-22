#app/api/v1/routers/responsables.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.responsable import ResponsableCreate, ResponsableRead, ResponsableUpdate
from app.schemas.common import ErrorResponse
from app.crud.responsable import get_responsable_by_usuario, create_responsable, update_responsable, delete_responsable
from app.utils.logger import logger

router = APIRouter(tags=["Responsables"])

#crear responsable
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

#listar responsables

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



#actualizar responsable
@router.put(
    "/{id}",
    response_model=ResponsableRead,
    responses={404: {"model": ErrorResponse}},
    summary="Actualizar responsable",
    description="Actualiza los datos de un responsable por su ID."
)
def update_responsable_endpoint(
    id: int,
    payload: ResponsableUpdate,
    db: Session = Depends(get_db),
):
    r = update_responsable(db, id, payload)
    if not r:
        raise HTTPException(status_code=404, detail="Responsable no encontrado")
    logger.info("Responsable actualizado", extra={"id": r.id, "usuario": r.usuario})
    return r

#eliminar responsable

@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
    summary="Eliminar responsable",
    description="Elimina un responsable por su ID."
)
def delete_responsable_endpoint(
    id: int,
    db: Session = Depends(get_db),
):
    ok = delete_responsable(db, id)
    if not ok:
        raise HTTPException(status_code=404, detail="Responsable no encontrado")
    logger.info("Responsable eliminado", extra={"id": id})
    return None