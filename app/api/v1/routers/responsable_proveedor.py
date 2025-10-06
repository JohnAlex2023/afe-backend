"""
Router API para gestión de asignaciones Responsable-Proveedor.
Permite asignar, listar, actualizar y eliminar responsables de proveedores.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.core.security import get_current_responsable, require_role
from app.utils.logger import logger
from app.models.responsable_proveedor import ResponsableProveedor
from app.models.responsable import Responsable
from app.models.proveedor import Proveedor
from pydantic import BaseModel


router = APIRouter(prefix="/responsable-proveedor", tags=["Responsable-Proveedor"])


# ==================== SCHEMAS ====================

class AsignacionCreate(BaseModel):
    responsable_id: int
    proveedor_id: int
    activo: bool = True


class AsignacionUpdate(BaseModel):
    responsable_id: Optional[int] = None
    activo: Optional[bool] = None


class AsignacionResponse(BaseModel):
    id: int
    responsable_id: int
    proveedor_id: int
    activo: bool
    creado_en: str
    responsable: dict
    proveedor: dict

    class Config:
        from_attributes = True


class AsignacionBulkCreate(BaseModel):
    """Para asignar múltiples proveedores a un responsable"""
    responsable_id: int
    proveedor_ids: List[int]
    activo: bool = True


# ==================== ENDPOINTS ====================

@router.get("/", response_model=List[AsignacionResponse])
def listar_asignaciones(
    skip: int = 0,
    limit: int = 100,
    responsable_id: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """
    Lista todas las asignaciones de responsable-proveedor.

    Filtros opcionales:
    - responsable_id: Filtrar por responsable
    - proveedor_id: Filtrar por proveedor
    - activo: Filtrar por estado activo/inactivo
    """
    query = db.query(ResponsableProveedor)

    if responsable_id is not None:
        query = query.filter(ResponsableProveedor.responsable_id == responsable_id)

    if proveedor_id is not None:
        query = query.filter(ResponsableProveedor.proveedor_id == proveedor_id)

    if activo is not None:
        query = query.filter(ResponsableProveedor.activo == activo)

    asignaciones = query.offset(skip).limit(limit).all()

    # Formatear respuesta con datos de responsable y proveedor
    resultado = []
    for asig in asignaciones:
        responsable = db.query(Responsable).filter(Responsable.id == asig.responsable_id).first()
        proveedor = db.query(Proveedor).filter(Proveedor.id == asig.proveedor_id).first()

        resultado.append({
            "id": asig.id,
            "responsable_id": asig.responsable_id,
            "proveedor_id": asig.proveedor_id,
            "activo": asig.activo,
            "creado_en": str(asig.creado_en) if asig.creado_en else None,
            "responsable": {
                "id": responsable.id,
                "usuario": responsable.usuario,
                "nombre": responsable.nombre,
                "email": responsable.email,
            } if responsable else None,
            "proveedor": {
                "id": proveedor.id,
                "nit": proveedor.nit,
                "razon_social": proveedor.razon_social,
                "area": proveedor.area,
            } if proveedor else None,
        })

    return resultado


@router.get("/{asignacion_id}", response_model=AsignacionResponse)
def obtener_asignacion(
    asignacion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """Obtiene una asignación específica por ID."""
    asig = db.query(ResponsableProveedor).filter(ResponsableProveedor.id == asignacion_id).first()

    if not asig:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación {asignacion_id} no encontrada"
        )

    responsable = db.query(Responsable).filter(Responsable.id == asig.responsable_id).first()
    proveedor = db.query(Proveedor).filter(Proveedor.id == asig.proveedor_id).first()

    return {
        "id": asig.id,
        "responsable_id": asig.responsable_id,
        "proveedor_id": asig.proveedor_id,
        "activo": asig.activo,
        "creado_en": str(asig.creado_en) if asig.creado_en else None,
        "responsable": {
            "id": responsable.id,
            "usuario": responsable.usuario,
            "nombre": responsable.nombre,
            "email": responsable.email,
        } if responsable else None,
        "proveedor": {
            "id": proveedor.id,
            "nit": proveedor.nit,
            "razon_social": proveedor.razon_social,
            "area": proveedor.area,
        } if proveedor else None,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_asignacion(
    payload: AsignacionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    """
    Crea una nueva asignación de responsable a proveedor.
    Solo administradores pueden crear asignaciones.
    """
    # Verificar que el responsable existe
    responsable = db.query(Responsable).filter(Responsable.id == payload.responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable {payload.responsable_id} no encontrado"
        )

    # Verificar que el proveedor existe
    proveedor = db.query(Proveedor).filter(Proveedor.id == payload.proveedor_id).first()
    if not proveedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proveedor {payload.proveedor_id} no encontrado"
        )

    # Verificar si ya existe la asignación
    asignacion_existente = db.query(ResponsableProveedor).filter(
        ResponsableProveedor.responsable_id == payload.responsable_id,
        ResponsableProveedor.proveedor_id == payload.proveedor_id
    ).first()

    if asignacion_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una asignación entre responsable {payload.responsable_id} y proveedor {payload.proveedor_id}"
        )

    # Crear asignación
    nueva_asignacion = ResponsableProveedor(
        responsable_id=payload.responsable_id,
        proveedor_id=payload.proveedor_id,
        activo=payload.activo
    )

    db.add(nueva_asignacion)
    db.commit()
    db.refresh(nueva_asignacion)

    logger.info(
        "Asignación creada",
        extra={
            "asignacion_id": nueva_asignacion.id,
            "responsable_id": payload.responsable_id,
            "proveedor_id": payload.proveedor_id,
            "usuario": current_user.usuario
        }
    )

    return {
        "id": nueva_asignacion.id,
        "responsable_id": nueva_asignacion.responsable_id,
        "proveedor_id": nueva_asignacion.proveedor_id,
        "activo": nueva_asignacion.activo,
        "mensaje": "Asignación creada exitosamente"
    }


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def crear_asignaciones_masivas(
    payload: AsignacionBulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    """
    Crea múltiples asignaciones de un responsable a varios proveedores.
    Útil para asignación masiva.
    """
    # Verificar que el responsable existe
    responsable = db.query(Responsable).filter(Responsable.id == payload.responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable {payload.responsable_id} no encontrado"
        )

    creadas = 0
    omitidas = 0
    errores = []

    for proveedor_id in payload.proveedor_ids:
        try:
            # Verificar que el proveedor existe
            proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
            if not proveedor:
                errores.append(f"Proveedor {proveedor_id} no encontrado")
                continue

            # Verificar si ya existe la asignación
            asignacion_existente = db.query(ResponsableProveedor).filter(
                ResponsableProveedor.responsable_id == payload.responsable_id,
                ResponsableProveedor.proveedor_id == proveedor_id
            ).first()

            if asignacion_existente:
                omitidas += 1
                continue

            # Crear asignación
            nueva_asignacion = ResponsableProveedor(
                responsable_id=payload.responsable_id,
                proveedor_id=proveedor_id,
                activo=payload.activo
            )

            db.add(nueva_asignacion)
            creadas += 1

        except Exception as e:
            errores.append(f"Error con proveedor {proveedor_id}: {str(e)}")

    db.commit()

    return {
        "total_procesados": len(payload.proveedor_ids),
        "creadas": creadas,
        "omitidas": omitidas,
        "errores": errores,
        "mensaje": f"Proceso completado: {creadas} asignaciones creadas, {omitidas} omitidas"
    }


@router.put("/{asignacion_id}")
def actualizar_asignacion(
    asignacion_id: int,
    payload: AsignacionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    """
    Actualiza una asignación existente.
    Permite cambiar el responsable o el estado activo.
    """
    asignacion = db.query(ResponsableProveedor).filter(
        ResponsableProveedor.id == asignacion_id
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación {asignacion_id} no encontrada"
        )

    # Actualizar campos
    if payload.responsable_id is not None:
        # Verificar que el nuevo responsable existe
        responsable = db.query(Responsable).filter(Responsable.id == payload.responsable_id).first()
        if not responsable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Responsable {payload.responsable_id} no encontrado"
            )

        # Verificar que no exista otra asignación con el nuevo responsable
        conflicto = db.query(ResponsableProveedor).filter(
            ResponsableProveedor.id != asignacion_id,
            ResponsableProveedor.responsable_id == payload.responsable_id,
            ResponsableProveedor.proveedor_id == asignacion.proveedor_id
        ).first()

        if conflicto:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una asignación entre responsable {payload.responsable_id} y este proveedor"
            )

        asignacion.responsable_id = payload.responsable_id

    if payload.activo is not None:
        asignacion.activo = payload.activo

    db.commit()
    db.refresh(asignacion)

    logger.info(
        "Asignación actualizada",
        extra={
            "asignacion_id": asignacion_id,
            "usuario": current_user.usuario
        }
    )

    return {
        "id": asignacion.id,
        "responsable_id": asignacion.responsable_id,
        "proveedor_id": asignacion.proveedor_id,
        "activo": asignacion.activo,
        "mensaje": "Asignación actualizada exitosamente"
    }


@router.delete("/{asignacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_asignacion(
    asignacion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    """
    Elimina una asignación de responsable-proveedor.
    Solo administradores pueden eliminar asignaciones.
    """
    asignacion = db.query(ResponsableProveedor).filter(
        ResponsableProveedor.id == asignacion_id
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación {asignacion_id} no encontrada"
        )

    db.delete(asignacion)
    db.commit()

    logger.info(
        "Asignación eliminada",
        extra={
            "asignacion_id": asignacion_id,
            "responsable_id": asignacion.responsable_id,
            "proveedor_id": asignacion.proveedor_id,
            "usuario": current_user.usuario
        }
    )

    return None


@router.get("/proveedor/{proveedor_id}/responsables")
def obtener_responsables_de_proveedor(
    proveedor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """Obtiene todos los responsables asignados a un proveedor."""
    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()

    if not proveedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proveedor {proveedor_id} no encontrado"
        )

    asignaciones = db.query(ResponsableProveedor).filter(
        ResponsableProveedor.proveedor_id == proveedor_id
    ).all()

    responsables = []
    for asig in asignaciones:
        resp = db.query(Responsable).filter(Responsable.id == asig.responsable_id).first()
        if resp:
            responsables.append({
                "asignacion_id": asig.id,
                "responsable_id": resp.id,
                "usuario": resp.usuario,
                "nombre": resp.nombre,
                "email": resp.email,
                "activo": asig.activo,
            })

    return {
        "proveedor_id": proveedor_id,
        "proveedor": {
            "nit": proveedor.nit,
            "razon_social": proveedor.razon_social,
        },
        "responsables": responsables,
        "total": len(responsables)
    }


@router.get("/responsable/{responsable_id}/proveedores")
def obtener_proveedores_de_responsable(
    responsable_id: int,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """Obtiene todos los proveedores asignados a un responsable."""
    responsable = db.query(Responsable).filter(Responsable.id == responsable_id).first()

    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable {responsable_id} no encontrado"
        )

    query = db.query(ResponsableProveedor).filter(
        ResponsableProveedor.responsable_id == responsable_id
    )

    if activo is not None:
        query = query.filter(ResponsableProveedor.activo == activo)

    asignaciones = query.all()

    proveedores = []
    for asig in asignaciones:
        prov = db.query(Proveedor).filter(Proveedor.id == asig.proveedor_id).first()
        if prov:
            proveedores.append({
                "asignacion_id": asig.id,
                "proveedor_id": prov.id,
                "nit": prov.nit,
                "razon_social": prov.razon_social,
                "area": prov.area,
                "activo": asig.activo,
            })

    return {
        "responsable_id": responsable_id,
        "responsable": {
            "usuario": responsable.usuario,
            "nombre": responsable.nombre,
        },
        "proveedores": proveedores,
        "total": len(proveedores)
    }
