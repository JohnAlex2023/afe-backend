#app/api/v1/routers/usuarios.py
"""
Router para gestión de Usuarios.

 IMPORTANTE: Algunos endpoints relacionados con usuario-proveedor
fueron movidos a /api/v1/asignacion-nit/*

  NUEVOS ENDPOINTS: Ver /api/v1/asignacion-nit/
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.usuario import UsuarioCreate, UsuarioRead, UsuarioUpdate
from app.schemas.common import ErrorResponse
from app.crud.usuario import (
    get_usuario_by_usuario,
    create_usuario,
    update_usuario,
    delete_usuario
)
from app.core.security import get_current_usuario, require_role
from app.utils.logger import logger

router = APIRouter(tags=["Usuarios"])


# ==================== ENDPOINTS DE USUARIOS ====================

@router.post(
    "/",
    response_model=UsuarioRead,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
    summary="Crear usuario",
    description="Crea un nuevo usuario en el sistema."
)
def create_usuario_endpoint(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Crea un nuevo usuario"""
    if get_usuario_by_usuario(db, payload.usuario):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario ya existe"
        )

    u = create_usuario(db, payload)
    logger.info("Usuario creado", extra={"id": u.id, "usuario": u.usuario})
    return u


@router.get(
    "/",
    response_model=List[UsuarioRead],
    summary="Listar usuarios",
    description="Obtiene todos los usuarios registrados."
)
def list_usuarios(
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable", "viewer")),
):
    """Lista todos los usuarios"""
    from app.models.usuario import Usuario
    return db.query(Usuario).all()


@router.get(
    "/{usuario_id}",
    response_model=UsuarioRead,
    summary="Obtener usuario por ID",
    description="Obtiene un usuario específico por su ID."
)
def get_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable", "viewer")),
):
    """Obtiene un usuario por ID"""
    from app.models.usuario import Usuario

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {usuario_id} no encontrado"
        )

    return usuario


@router.put(
    "/{usuario_id}",
    response_model=UsuarioRead,
    summary="Actualizar usuario",
    description="Actualiza la información de un usuario."
)
def update_usuario_endpoint(
    usuario_id: int,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Actualiza un usuario"""
    try:
        usuario = update_usuario(db, usuario_id, payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {usuario_id} no encontrado"
        )

    logger.info(f"Usuario actualizado: {usuario_id}")
    return usuario


@router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario",
    description="Elimina (desactiva) un usuario del sistema."
)
def delete_usuario_endpoint(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Elimina (desactiva) un usuario"""
    success = delete_usuario(db, usuario_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {usuario_id} no encontrado"
        )

    logger.info(f"Usuario eliminado: {usuario_id}")
    return None


# ==================== ENDPOINT DE DIAGNÓSTICO ====================

@router.get(
    "/me/diagnostico",
    summary="Diagnóstico del usuario actual",
    description="Retorna información de diagnóstico sobre el usuario autenticado y sus asignaciones"
)
def diagnostico_usuario(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario),
):
    """
    Retorna:
    - ID y nombre del usuario actual
    - Total de asignaciones en AsignacionNitResponsable
    - Total de facturas donde responsable_id = current_user.id
    - IDs de proveedores según _obtener_proveedor_ids_de_responsable()
    """
    from app.models.workflow_aprobacion import AsignacionNitResponsable
    from app.models.factura import Factura
    from app.crud.factura import _obtener_proveedor_ids_de_responsable
    from sqlalchemy import func

    # Info del usuario
    usuario_info = {
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
        "usuario": usuario_info,
        "asignaciones_explicitas": asignaciones_info,
        "facturas_donde_responsable_id_es_actual": total_facturas_directas,
        "proveedor_ids_obtenidos": proveedor_ids,
        "facturas_de_esos_proveedores": facturas_filtradas,
        "nota": "Si 'asignaciones_explicitas.total' > 0, se usan esos NITs. Si = 0, se usan facturas_donde_responsable_id_es_actual"
    }


# ==================== ENDPOINTS DE ASIGNACIONES ====================
#  NOTA: Los endpoints de asignación usuario-proveedor fueron
# movidos a /api/v1/asignacion-nit/*
#
# - GET /asignacion-nit/ - Listar asignaciones
# - POST /asignacion-nit/ - Crear asignación
# - PUT /asignacion-nit/{id} - Actualizar asignación
# - DELETE /asignacion-nit/{id} - Eliminar asignación
# - POST /asignacion-nit/bulk - Asignación masiva
# - GET /asignacion-nit/por-responsable/{responsable_id} - Asignaciones por usuario
#
# ==================== FIN DEL ARCHIVO ====================
