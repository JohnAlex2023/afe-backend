#app/api/v1/routers/responsables.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.responsable import ResponsableCreate, ResponsableRead, ResponsableNitCreate, ResponsableNitRead
from app.schemas.common import ErrorResponse
from app.crud.responsable import get_responsable_by_usuario, create_responsable, get_nits_by_responsable, create_nit_for_responsable, delete_nit
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


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar responsable",
    description="Elimina un responsable por su id. Retorna 204 si fue eliminado, 404 si no existe."
)
def delete_responsable_endpoint(id: int, db: Session = Depends(get_db)):
    from app.crud.responsable import delete_responsable
    eliminado = delete_responsable(db, id)
    if not eliminado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Responsable no encontrado")
    return None

#tabla de nit_responsable
@router.get(
    "/{responsable_id}/nits/",
    response_model=List[ResponsableNitRead],
    summary="Listar NITs de un responsable",
    description="Obtiene todos los NITs asociados a un responsable."
)
def list_nits_responsable(responsable_id: int, db: Session = Depends(get_db)):
    return get_nits_by_responsable(db, responsable_id)


@router.post(
    "/{responsable_id}/nits/",
    response_model=ResponsableNitRead,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar NIT a responsable",
    description="Agrega un nuevo NIT a un responsable."
)
def add_nit_responsable(responsable_id: int, payload: ResponsableNitCreate, db: Session = Depends(get_db)):
    return create_nit_for_responsable(db, responsable_id, payload)


@router.delete(
    "/{responsable_id}/nits/{nit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar NIT de responsable",
    description="Elimina un NIT específico de un responsable."
)
def delete_nit_responsable(responsable_id: int, nit_id: int, db: Session = Depends(get_db)):
    eliminado = delete_nit(db, nit_id)
    if not eliminado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NIT no encontrado")
    return None
