#app/api/v1/routers/responsables.py
"""
Router para gestión de Responsables.

 IMPORTANTE: Algunos endpoints relacionados con responsable-proveedor
fueron movidos a /api/v1/asignacion-nit/*

  NUEVOS ENDPOINTS: Ver /api/v1/asignacion-nit/
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.responsable import ResponsableCreate, ResponsableRead, ResponsableUpdate
from app.schemas.common import ErrorResponse
from app.crud.responsable import (
    get_responsable_by_usuario,
    create_responsable,
    update_responsable,
    delete_responsable
)
from app.core.security import get_current_responsable, require_role
from app.utils.logger import logger

router = APIRouter(tags=["Responsables"])


# ==================== ENDPOINTS DE RESPONSABLES ====================

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
    current_user=Depends(require_role("admin")),
):
    """Crea un nuevo responsable"""
    if get_responsable_by_usuario(db, payload.usuario):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario ya existe"
        )

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
    current_user=Depends(require_role("admin", "responsable")),
):
    """Lista todos los responsables"""
    from app.models.responsable import Responsable
    return db.query(Responsable).all()


@router.get(
    "/{responsable_id}",
    response_model=ResponsableRead,
    summary="Obtener responsable por ID",
    description="Obtiene un responsable específico por su ID."
)
def get_responsable(
    responsable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable")),
):
    """Obtiene un responsable por ID"""
    from app.models.responsable import Responsable

    responsable = db.query(Responsable).filter(Responsable.id == responsable_id).first()

    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable con ID {responsable_id} no encontrado"
        )

    return responsable


@router.put(
    "/{responsable_id}",
    response_model=ResponsableRead,
    summary="Actualizar responsable",
    description="Actualiza la información de un responsable."
)
def update_responsable_endpoint(
    responsable_id: int,
    payload: ResponsableUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Actualiza un responsable"""
    responsable = update_responsable(db, responsable_id, payload)

    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable con ID {responsable_id} no encontrado"
        )

    logger.info(f"Responsable actualizado: {responsable_id}")
    return responsable


@router.delete(
    "/{responsable_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar responsable",
    description="Elimina (desactiva) un responsable del sistema."
)
def delete_responsable_endpoint(
    responsable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Elimina (desactiva) un responsable"""
    success = delete_responsable(db, responsable_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable con ID {responsable_id} no encontrado"
        )

    logger.info(f"Responsable eliminado: {responsable_id}")
    return None


# ==================== ENDPOINT DE DIAGNÓSTICO ====================

@router.get(
    "/me/diagnostico",
    summary="Diagnóstico del responsable actual",
    description="Retorna información de diagnóstico sobre el responsable autenticado y sus asignaciones"
)
def diagnostico_responsable(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Retorna:
    - ID y nombre del responsable actual
    - Total de asignaciones en AsignacionNitResponsable
    - Total de facturas donde responsable_id = current_user.id
    - IDs de proveedores según _obtener_proveedor_ids_de_responsable()
    """
    from app.models.workflow_aprobacion import AsignacionNitResponsable
    from app.models.factura import Factura
    from app.crud.factura import _obtener_proveedor_ids_de_responsable
    from sqlalchemy import func

    # Info del responsable
    responsable_info = {
        "id": current_user.id,
        "usuario": current_user.usuario,
        "nombre": current_user.nombre,
        "rol": current_user.role.nombre if hasattr(current_user, 'role') and current_user.role else None,
    }

    # Asignaciones explícitas en AsignacionNitResponsable
    asignaciones = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.responsable_id == current_user.id,
        AsignacionNitResponsable.activo == True
    ).all()

    asignaciones_info = {
        "total": len(asignaciones),
        "nits": [a.nit for a in asignaciones],
        "proveedores": [a.nombre_proveedor for a in asignaciones]
    }

    # Facturas donde responsable_id = current_user.id
    total_facturas_directas = db.query(func.count(Factura.id)).filter(
        Factura.responsable_id == current_user.id
    ).scalar()

    # Usar la función _obtener_proveedor_ids_de_responsable
    proveedor_ids = _obtener_proveedor_ids_de_responsable(db, current_user.id)

    # Contar facturas de esos proveedores
    facturas_filtradas = db.query(func.count(Factura.id)).filter(
        Factura.proveedor_id.in_(proveedor_ids) if proveedor_ids else None
    ).scalar() if proveedor_ids else 0

    return {
        "responsable": responsable_info,
        "asignaciones_explicitas": asignaciones_info,
        "facturas_donde_responsable_id_es_actual": total_facturas_directas,
        "proveedor_ids_obtenidos": proveedor_ids,
        "facturas_de_esos_proveedores": facturas_filtradas,
        "nota": "Si 'asignaciones_explicitas.total' > 0, se usan esos NITs. Si = 0, se usan facturas_donde_responsable_id_es_actual"
    }


# ==================== ENDPOINTS DE ASIGNACIONES ====================
#  NOTA: Los endpoints de asignación responsable-proveedor fueron
# movidos a /api/v1/asignacion-nit/*
#
# - GET /asignacion-nit/ - Listar asignaciones
# - POST /asignacion-nit/ - Crear asignación
# - PUT /asignacion-nit/{id} - Actualizar asignación
# - DELETE /asignacion-nit/{id} - Eliminar asignación
# - POST /asignacion-nit/bulk - Asignación masiva
# - GET /asignacion-nit/por-responsable/{responsable_id} - Asignaciones por responsable
#
# ==================== FIN DEL ARCHIVO ====================
