"""
Router API para gestión de asignaciones NIT-Responsable.
Reemplazo de responsable_proveedor, usando SOLO asignacion_nit_responsable.

✅ NUEVA ARQUITECTURA UNIFICADA
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.core.security import get_current_responsable, require_role
from app.utils.logger import logger
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.responsable import Responsable
from app.models.proveedor import Proveedor
from app.models.factura import Factura
from pydantic import BaseModel


router = APIRouter(prefix="/asignacion-nit", tags=["Asignación NIT-Responsable"])


# ==================== SCHEMAS ====================

class AsignacionNitCreate(BaseModel):
    """Crear nueva asignación NIT → Responsable"""
    nit: str
    responsable_id: int
    nombre_proveedor: Optional[str] = None
    area: Optional[str] = None
    permitir_aprobacion_automatica: bool = True
    requiere_revision_siempre: bool = False


class AsignacionNitUpdate(BaseModel):
    """Actualizar asignación existente"""
    responsable_id: Optional[int] = None
    nombre_proveedor: Optional[str] = None
    area: Optional[str] = None
    permitir_aprobacion_automatica: Optional[bool] = None
    requiere_revision_siempre: Optional[bool] = None
    activo: Optional[bool] = None


class ResponsableSimple(BaseModel):
    """Información básica del responsable"""
    id: int
    usuario: str
    nombre: str
    email: str
    area: Optional[str] = None

    class Config:
        from_attributes = True


class AsignacionNitResponse(BaseModel):
    """Respuesta de asignación"""
    id: int
    nit: str
    nombre_proveedor: Optional[str]
    responsable_id: int
    area: Optional[str]
    permitir_aprobacion_automatica: bool
    requiere_revision_siempre: bool
    activo: bool
    # Objeto responsable completo para compatibilidad con frontend
    responsable: Optional[ResponsableSimple] = None

    class Config:
        from_attributes = True


class NitBulkItem(BaseModel):
    """Item individual para creación bulk"""
    nit: str
    nombre_proveedor: str
    area: Optional[str] = None


class AsignacionBulkCreate(BaseModel):
    """Asignar múltiples NITs a un responsable"""
    responsable_id: int
    nits: List[NitBulkItem]
    permitir_aprobacion_automatica: Optional[bool] = True
    activo: Optional[bool] = True


# ==================== FUNCIONES AUXILIARES ====================

def sincronizar_facturas_por_nit(db: Session, nit: str, responsable_id: int):
    """
    Actualiza todas las facturas de un NIT para asignarles el responsable correcto.
    """
    # Obtener proveedores con ese NIT
    proveedores = db.query(Proveedor).filter(Proveedor.nit == nit).all()

    total_facturas = 0
    for proveedor in proveedores:
        facturas = db.query(Factura).filter(Factura.proveedor_id == proveedor.id).all()
        for factura in facturas:
            factura.responsable_id = responsable_id
            total_facturas += 1

    logger.info(f"Sincronizadas {total_facturas} facturas para NIT {nit} → Responsable {responsable_id}")
    return total_facturas


# ==================== ENDPOINTS ====================

@router.get("/", response_model=List[AsignacionNitResponse])
def listar_asignaciones_nit(
    skip: int = 0,
    limit: int = 100,
    responsable_id: Optional[int] = Query(None),
    nit: Optional[str] = Query(None),
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """
    Lista todas las asignaciones NIT → Responsable.

    Filtros opcionales:
    - responsable_id: Filtrar por responsable
    - nit: Filtrar por NIT específico
    - activo: Filtrar por estado activo/inactivo
    """
    query = db.query(AsignacionNitResponsable)

    if responsable_id is not None:
        query = query.filter(AsignacionNitResponsable.responsable_id == responsable_id)

    if nit is not None:
        query = query.filter(AsignacionNitResponsable.nit == nit)

    if activo is not None:
        query = query.filter(AsignacionNitResponsable.activo == activo)

    asignaciones = query.offset(skip).limit(limit).all()

    # Enriquecer con datos completos del responsable
    resultado = []
    for asig in asignaciones:
        responsable = db.query(Responsable).filter(Responsable.id == asig.responsable_id).first()
        asig_dict = {
            "id": asig.id,
            "nit": asig.nit,
            "nombre_proveedor": asig.nombre_proveedor,
            "responsable_id": asig.responsable_id,
            "area": asig.area,
            "permitir_aprobacion_automatica": asig.permitir_aprobacion_automatica,
            "requiere_revision_siempre": asig.requiere_revision_siempre,
            "activo": asig.activo,
            "responsable": ResponsableSimple.from_orm(responsable) if responsable else None
        }
        resultado.append(AsignacionNitResponse(**asig_dict))

    return resultado


@router.post("/", response_model=AsignacionNitResponse, status_code=status.HTTP_201_CREATED)
def crear_asignacion_nit(
    payload: AsignacionNitCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)  # Cualquier usuario autenticado
):
    """
    Crea una nueva asignación NIT → Responsable.

    Automáticamente sincroniza todas las facturas existentes de ese NIT.
    """
    # Verificar que el responsable existe
    responsable = db.query(Responsable).filter(Responsable.id == payload.responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable con ID {payload.responsable_id} no encontrado"
        )

    # Verificar si ya existe asignación para este NIT
    existente = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.nit == payload.nit
    ).first()

    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una asignación para el NIT {payload.nit}"
        )

    # Crear asignación
    nueva_asignacion = AsignacionNitResponsable(
        nit=payload.nit,
        nombre_proveedor=payload.nombre_proveedor,
        responsable_id=payload.responsable_id,
        area=payload.area or responsable.area,
        permitir_aprobacion_automatica=payload.permitir_aprobacion_automatica,
        requiere_revision_siempre=payload.requiere_revision_siempre,
        activo=True
    )

    db.add(nueva_asignacion)
    db.flush()

    # Sincronizar facturas existentes
    total_facturas = sincronizar_facturas_por_nit(db, payload.nit, payload.responsable_id)

    db.commit()
    db.refresh(nueva_asignacion)

    logger.info(
        f"Asignación NIT creada: {payload.nit} → Responsable {payload.responsable_id} "
        f"({total_facturas} facturas sincronizadas)"
    )

    return AsignacionNitResponse(
        **nueva_asignacion.__dict__,
        responsable=ResponsableSimple.from_orm(responsable)
    )


@router.put("/{asignacion_id}", response_model=AsignacionNitResponse)
def actualizar_asignacion_nit(
    asignacion_id: int,
    payload: AsignacionNitUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)  # Cualquier usuario autenticado
):
    """
    Actualiza una asignación NIT → Responsable existente.

    Si cambia el responsable_id, sincroniza automáticamente todas las facturas.
    """
    asignacion = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.id == asignacion_id
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación con ID {asignacion_id} no encontrada"
        )

    # Guardar responsable anterior para detectar cambio
    responsable_anterior = asignacion.responsable_id

    # Actualizar campos
    if payload.responsable_id is not None:
        asignacion.responsable_id = payload.responsable_id
    if payload.nombre_proveedor is not None:
        asignacion.nombre_proveedor = payload.nombre_proveedor
    if payload.area is not None:
        asignacion.area = payload.area
    if payload.permitir_aprobacion_automatica is not None:
        asignacion.permitir_aprobacion_automatica = payload.permitir_aprobacion_automatica
    if payload.requiere_revision_siempre is not None:
        asignacion.requiere_revision_siempre = payload.requiere_revision_siempre
    if payload.activo is not None:
        asignacion.activo = payload.activo

    # Si cambió el responsable, sincronizar facturas
    if payload.responsable_id and payload.responsable_id != responsable_anterior:
        total_facturas = sincronizar_facturas_por_nit(db, asignacion.nit, payload.responsable_id)
        logger.info(f"Responsable cambiado: {responsable_anterior} → {payload.responsable_id}, {total_facturas} facturas sincronizadas")

    db.commit()
    db.refresh(asignacion)

    # Obtener datos completos del responsable
    responsable = db.query(Responsable).filter(Responsable.id == asignacion.responsable_id).first()

    return AsignacionNitResponse(
        **asignacion.__dict__,
        responsable=ResponsableSimple.from_orm(responsable) if responsable else None
    )


@router.delete("/{asignacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_asignacion_nit(
    asignacion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)  # Cualquier usuario autenticado
):
    """
    Elimina (marca como inactiva) una asignación NIT → Responsable.

    Las facturas existentes mantienen su responsable asignado.
    """
    asignacion = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.id == asignacion_id
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación con ID {asignacion_id} no encontrada"
        )

    # Marcar como inactiva en lugar de eliminar
    asignacion.activo = False

    db.commit()

    logger.info(f"Asignación NIT desactivada: {asignacion.nit}")

    return None


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def crear_asignaciones_bulk(
    payload: AsignacionBulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin"]))
):
    """
    Asigna múltiples NITs a un responsable de una sola vez.

    Retorna cuántas asignaciones se crearon exitosamente.
    """
    # Verificar responsable
    responsable = db.query(Responsable).filter(Responsable.id == payload.responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable con ID {payload.responsable_id} no encontrado"
        )

    creadas = 0
    actualizadas = 0
    omitidas = 0
    errores = []

    for nit_item in payload.nits:
        try:
            # Verificar si ya existe
            existente = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == nit_item.nit
            ).first()

            if existente:
                # Actualizar
                existente.responsable_id = payload.responsable_id
                existente.nombre_proveedor = nit_item.nombre_proveedor
                existente.area = nit_item.area or responsable.area
                existente.permitir_aprobacion_automatica = payload.permitir_aprobacion_automatica
                existente.activo = payload.activo
                sincronizar_facturas_por_nit(db, nit_item.nit, payload.responsable_id)
                actualizadas += 1
            else:
                # Crear nueva
                nueva = AsignacionNitResponsable(
                    nit=nit_item.nit,
                    nombre_proveedor=nit_item.nombre_proveedor,
                    responsable_id=payload.responsable_id,
                    area=nit_item.area or responsable.area,
                    permitir_aprobacion_automatica=payload.permitir_aprobacion_automatica,
                    requiere_revision_siempre=False,
                    activo=payload.activo
                )
                db.add(nueva)
                sincronizar_facturas_por_nit(db, nit_item.nit, payload.responsable_id)
                creadas += 1

        except Exception as e:
            errores.append(f"NIT {nit_item.nit}: {str(e)}")

    db.commit()

    logger.info(
        f"Asignación bulk completada: {creadas} creadas, {actualizadas} actualizadas, {len(errores)} errores"
    )

    return {
        "total_procesados": len(payload.nits),
        "creadas": creadas,
        "actualizadas": actualizadas,
        "omitidas": omitidas,
        "errores": errores
    }


@router.get("/por-responsable/{responsable_id}", response_model=List[AsignacionNitResponse])
def obtener_asignaciones_por_responsable(
    responsable_id: int,
    activo: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """
    Obtiene todas las asignaciones de un responsable específico.
    """
    asignaciones = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.responsable_id == responsable_id,
        AsignacionNitResponsable.activo == activo
    ).all()

    responsable = db.query(Responsable).filter(Responsable.id == responsable_id).first()

    resultado = []
    for asig in asignaciones:
        resultado.append(AsignacionNitResponse(
            **asig.__dict__,
            responsable_nombre=responsable.nombre if responsable else None
        ))

    return resultado
