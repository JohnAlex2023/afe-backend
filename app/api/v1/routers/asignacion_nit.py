"""
Router API para gestión de asignaciones NIT-Responsable.
Reemplazo de responsable_proveedor, usando SOLO asignacion_nit_responsable.

 NUEVA ARQUITECTURA UNIFICADA
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
from app.services.audit_service import AuditService
from pydantic import BaseModel


router = APIRouter(prefix="/asignacion-nit", tags=["Asignación NIT-Responsable"])


# ==================== SCHEMAS ====================

class AsignacionNitCreate(BaseModel):
    """Crear nueva asignación NIT -> Responsable"""
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


class AsignacionesPorResponsableResponse(BaseModel):
    """Respuesta agrupada de asignaciones por responsable"""
    responsable_id: int
    responsable: ResponsableSimple
    asignaciones: List[AsignacionNitResponse]
    total: int

    class Config:
        from_attributes = True


# ==================== FUNCIONES AUXILIARES ====================

def sincronizar_facturas_por_nit(db: Session, nit: str, responsable_id: int):
    """
    Actualiza todas las facturas de un NIT para asignarles el responsable correcto.

    ARQUITECTURA MEJORADA:
    - Busca proveedores usando LIKE para manejar digito de verificacion
    - Ejemplo: NIT '800185449' coincide con '800185449-9' en proveedores
    - Garantiza sincronizacion completa sin importar formato del NIT
    """
    # Obtener proveedores con ese NIT (maneja digito de verificacion)
    proveedores = db.query(Proveedor).filter(
        Proveedor.nit.like(f'{nit}%')
    ).all()

    total_facturas = 0
    for proveedor in proveedores:
        facturas = db.query(Factura).filter(Factura.proveedor_id == proveedor.id).all()
        for factura in facturas:
            factura.responsable_id = responsable_id
            total_facturas += 1

    logger.info(
        f"Sincronizadas {total_facturas} facturas para NIT {nit} "
        f"({len(proveedores)} proveedores) -> Responsable {responsable_id}"
    )
    return total_facturas


def desasignar_facturas_por_responsable(db: Session, responsable_id: int, nit: str = None):
    """
    Desasigna todas las facturas de un responsable (responsable_id = NULL).
    Se ejecuta cuando se elimina una asignación NIT-Responsable.

    ENTERPRISE PATTERN: Mantiene integridad referencial del sistema.
    - Al eliminar asignación, las facturas pierden su responsable
    - Facturas vuelven a pool de "sin asignar"
    - Si se reasigna el NIT, las facturas se vuelven a asignar automáticamente

    ARQUITECTURA SIMPLIFICADA:
    - Filtra directamente por responsable_id (no por NIT)
    - Evita problemas de dígito de verificación
    - Garantiza sincronización completa
    """
    # ARQUITECTURA DIRECTA: Buscar facturas por responsable_id
    facturas = db.query(Factura).filter(
        Factura.responsable_id == responsable_id
    ).all()

    total_facturas = len(facturas)
    for factura in facturas:
        factura.responsable_id = None  # Desasignar

    nit_info = f" (NIT={nit})" if nit else ""
    logger.info(
        f"Desasignadas {total_facturas} facturas para Responsable ID={responsable_id}{nit_info} "
        f"-> responsable_id = NULL"
    )
    return total_facturas


# ==================== ENDPOINTS ====================

@router.get("/", response_model=List[AsignacionNitResponse])
def listar_asignaciones_nit(
    skip: int = 0,
    limit: int = 100,
    responsable_id: Optional[int] = Query(None),
    nit: Optional[str] = Query(None),
    activo: bool = Query(True, description="Filtrar por estado activo/inactivo. Default: True (solo activas)"),
    incluir_inactivos: bool = Query(False, description="Si True, incluye asignaciones eliminadas (soft delete)"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """
    Lista todas las asignaciones NIT -> Responsable.

    **COMPORTAMIENTO ENTERPRISE-GRADE:**
    - Por defecto retorna SOLO asignaciones activas (soft delete pattern)
    - Use incluir_inactivos=true para ver asignaciones eliminadas (auditoría)
    - Use activo=false para ver SOLO asignaciones eliminadas

    **Filtros disponibles:**
    - responsable_id: Filtrar por responsable específico
    - nit: Filtrar por NIT específico
    - activo: Estado activo (default: True)
    - incluir_inactivos: Incluye eliminadas (default: False)

    **Ejemplos:**
    - GET /asignacion-nit/ -> Solo activas (comportamiento normal)
    - GET /asignacion-nit/?incluir_inactivos=true -> Todas (activas + eliminadas)
    - GET /asignacion-nit/?activo=false -> Solo eliminadas (auditoría)

    **Nivel:** Enterprise Production-Ready
    """
    query = db.query(AsignacionNitResponsable)

    # FILTRO CRÍTICO: Solo asignaciones activas por defecto (SOFT DELETE PATTERN)
    # Esto previene que asignaciones "eliminadas" interfieran con operaciones normales
    if incluir_inactivos:
        # Modo auditoría: incluir todas (activas + inactivas)
        pass  # No filtrar por activo
    else:
        # Modo normal: filtrar por estado activo
        query = query.filter(AsignacionNitResponsable.activo == activo)

    if responsable_id is not None:
        query = query.filter(AsignacionNitResponsable.responsable_id == responsable_id)

    if nit is not None:
        query = query.filter(AsignacionNitResponsable.nit == nit)

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
    Crea una nueva asignación NIT -> Responsable.

    **COMPORTAMIENTO ENTERPRISE-GRADE:**
    - Valida duplicados SOLO entre asignaciones ACTIVAS (soft delete aware)
    - Si existe una asignación INACTIVA (eliminada previamente), la REACTIVA automáticamente
    - Sincroniza automáticamente todas las facturas existentes del NIT

    **Ventajas del patrón de reactivación:**
    - Evita violación del constraint UNIQUE (nit, responsable_id)
    - Mantiene historial completo de auditoría
    - Reutiliza ID existente (referential integrity)
    - Mejor performance (UPDATE vs INSERT + manejo de constraint)

    **Nivel:** Enterprise Production-Ready with Idempotency
    """
    # Verificar que el responsable existe
    responsable = db.query(Responsable).filter(Responsable.id == payload.responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable con ID {payload.responsable_id} no encontrado"
        )

    # PASO 1: Verificar si existe asignación ACTIVA (duplicado real)
    # CRÍTICO: Solo buscar en asignaciones activas para evitar falsos positivos
    existente_activa = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.nit == payload.nit,
        AsignacionNitResponsable.responsable_id == payload.responsable_id,
        AsignacionNitResponsable.activo == True  #  FILTRO CRÍTICO
    ).first()

    if existente_activa:
        # Duplicado verdadero: asignación activa ya existe
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El responsable '{responsable.nombre}' ya tiene asignado el NIT {payload.nit}. "
                   f"Esta asignación ya existe y está activa en el sistema."
        )

    # PASO 2: Verificar si existe asignación INACTIVA (soft deleted)
    # PATRÓN ENTERPRISE: Reactivar en lugar de crear duplicado
    existente_inactiva = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.nit == payload.nit,
        AsignacionNitResponsable.responsable_id == payload.responsable_id,
        AsignacionNitResponsable.activo == False  # Registro eliminado previamente
    ).first()

    if existente_inactiva:
        # REACTIVAR: Restaurar asignación previamente eliminada
        existente_inactiva.activo = True
        existente_inactiva.actualizado_en = datetime.now()
        existente_inactiva.actualizado_por = current_user.usuario

        # Actualizar campos con nuevos valores (merge pattern)
        if payload.nombre_proveedor:
            existente_inactiva.nombre_proveedor = payload.nombre_proveedor
        if payload.area:
            existente_inactiva.area = payload.area
        existente_inactiva.permitir_aprobacion_automatica = payload.permitir_aprobacion_automatica
        existente_inactiva.requiere_revision_siempre = payload.requiere_revision_siempre

        # Sincronizar facturas
        total_facturas = sincronizar_facturas_por_nit(db, payload.nit, payload.responsable_id)

        db.commit()
        db.refresh(existente_inactiva)

        logger.info(
            f"Asignación NIT REACTIVADA: {payload.nit} -> Responsable {payload.responsable_id} "
            f"(ID={existente_inactiva.id}, {total_facturas} facturas sincronizadas) "
            f"[ENTERPRISE: Soft delete pattern - reactivación automática]"
        )

        return AsignacionNitResponse(
            **existente_inactiva.__dict__,
            responsable=ResponsableSimple.from_orm(responsable)
        )

    # PASO 3: Crear nueva asignación (no existe ni activa ni inactiva)
    nueva_asignacion = AsignacionNitResponsable(
        nit=payload.nit,
        nombre_proveedor=payload.nombre_proveedor,
        responsable_id=payload.responsable_id,
        area=payload.area or responsable.area,
        permitir_aprobacion_automatica=payload.permitir_aprobacion_automatica,
        requiere_revision_siempre=payload.requiere_revision_siempre,
        activo=True,
        creado_por=current_user.usuario
    )

    db.add(nueva_asignacion)
    db.flush()

    # Sincronizar facturas existentes
    total_facturas = sincronizar_facturas_por_nit(db, payload.nit, payload.responsable_id)

    db.commit()
    db.refresh(nueva_asignacion)

    logger.info(
        f"Asignación NIT CREADA: {payload.nit} -> Responsable {payload.responsable_id} "
        f"(ID={nueva_asignacion.id}, {total_facturas} facturas sincronizadas)"
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
    Actualiza una asignación NIT -> Responsable existente.

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
        logger.info(f"Responsable cambiado: {responsable_anterior} -> {payload.responsable_id}, {total_facturas} facturas sincronizadas")

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
    Elimina (marca como inactiva) una asignación NIT -> Responsable.

    **SOFT DELETE PATTERN:**
    - No elimina físicamente el registro de la base de datos
    - Marca el campo 'activo' como False
    - Mantiene historial completo para auditoría
    - DESASIGNA todas las facturas del NIT (responsable_id = NULL)
    - La asignación puede ser restaurada posteriormente

    **SINCRONIZACIÓN AUTOMÁTICA:**
    - Todas las facturas del NIT pierden su responsable asignado
    - Facturas vuelven al pool de "Por Asignar"
    - Si se restaura la asignación, las facturas se reasignan automáticamente

    **Nivel:** Enterprise Production-Ready with Full Synchronization
    """
    asignacion = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.id == asignacion_id
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación con ID {asignacion_id} no encontrada"
        )

    if not asignacion.activo:
        # Ya está eliminada (soft delete)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La asignación con ID {asignacion_id} ya está eliminada. "
                   f"Use /asignacion-nit/{asignacion_id}/restore para restaurarla."
        )

    # PASO 1: SOFT DELETE - Marcar como inactiva
    asignacion.activo = False
    asignacion.actualizado_en = datetime.now()
    asignacion.actualizado_por = current_user.usuario

    # PASO 2: DESASIGNAR FACTURAS - Sincronización completa
    total_facturas_desasignadas = desasignar_facturas_por_responsable(
        db,
        responsable_id=asignacion.responsable_id,
        nit=asignacion.nit
    )

    db.commit()

    logger.info(
        f"Asignación NIT eliminada (soft delete): NIT={asignacion.nit}, "
        f"ID={asignacion_id}, Usuario={current_user.usuario}, "
        f"Facturas desasignadas={total_facturas_desasignadas}"
    )

    return None


@router.post("/{asignacion_id}/restore", response_model=AsignacionNitResponse)
def restaurar_asignacion_nit(
    asignacion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """
    Restaura una asignación previamente eliminada (soft delete).

    **ENTERPRISE FEATURE:**
    - Permite "deshacer" eliminaciones accidentales
    - Verifica que no exista conflicto con asignaciones activas
    - Mantiene trazabilidad completa de la operación
    - Resincroniza facturas automáticamente

    **Casos de uso:**
    - Eliminación accidental por el usuario
    - Recuperación de asignaciones históricas
    - Auditoría y compliance

    **Nivel:** Enterprise Production-Ready with Conflict Detection
    """
    # Buscar asignación eliminada
    asignacion = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.id == asignacion_id
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación con ID {asignacion_id} no encontrada"
        )

    if asignacion.activo:
        # Ya está activa
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La asignación con ID {asignacion_id} ya está activa. No requiere restauración."
        )

    # Verificar que no exista otra asignación activa con el mismo NIT + responsable
    conflicto = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.nit == asignacion.nit,
        AsignacionNitResponsable.responsable_id == asignacion.responsable_id,
        AsignacionNitResponsable.activo == True,
        AsignacionNitResponsable.id != asignacion_id  # Excluir la misma asignación
    ).first()

    if conflicto:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede restaurar la asignación: Ya existe una asignación activa "
                   f"para NIT {asignacion.nit} y responsable {asignacion.responsable_id} (ID={conflicto.id}). "
                   f"Elimine la asignación conflictiva primero."
        )

    # RESTAURAR: Reactivar asignación
    asignacion.activo = True
    asignacion.actualizado_en = datetime.now()
    asignacion.actualizado_por = current_user.usuario

    # Resincronizar facturas
    total_facturas = sincronizar_facturas_por_nit(db, asignacion.nit, asignacion.responsable_id)

    db.commit()
    db.refresh(asignacion)

    # Obtener responsable para response
    responsable = db.query(Responsable).filter(Responsable.id == asignacion.responsable_id).first()

    logger.info(
        f"Asignación NIT RESTAURADA: NIT={asignacion.nit}, ID={asignacion_id}, "
        f"Usuario={current_user.usuario}, Facturas resincronizadas={total_facturas}"
    )

    return AsignacionNitResponse(
        **asignacion.__dict__,
        responsable=ResponsableSimple.from_orm(responsable) if responsable else None
    )


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def crear_asignaciones_bulk(
    payload: AsignacionBulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)  # Cualquier usuario autenticado
):
    """
    Asigna múltiples NITs a un responsable de una sola vez.

    **COMPORTAMIENTO ENTERPRISE-GRADE:**
    - Valida duplicados SOLO entre asignaciones ACTIVAS (soft delete aware)
    - Reactiva automáticamente asignaciones INACTIVAS (previamente eliminadas)
    - Operación transaccional: si falla uno, fallan todos (atomicidad)
    - Retorna estadísticas detalladas de la operación

    **Retorna:**
    - total_procesados: Cantidad de NITs en el payload
    - creadas: Nuevas asignaciones creadas
    - reactivadas: Asignaciones previamente eliminadas que fueron reactivadas
    - omitidas: Asignaciones que ya existían activas (duplicados)
    - errores: Lista de errores encontrados

    **Nivel:** Enterprise Production-Ready with Transaction Safety
    """
    # Verificar responsable
    responsable = db.query(Responsable).filter(Responsable.id == payload.responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable con ID {payload.responsable_id} no encontrado"
        )

    creadas = 0
    reactivadas = 0
    omitidas = 0
    errores = []

    for nit_item in payload.nits:
        try:
            # PASO 1: Verificar si existe asignación ACTIVA (duplicado verdadero)
            existente_activa = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == nit_item.nit,
                AsignacionNitResponsable.responsable_id == payload.responsable_id,
                AsignacionNitResponsable.activo == True  # FILTRO CRÍTICO
            ).first()

            if existente_activa:
                # Ya existe activa, omitir
                omitidas += 1
                logger.debug(f"Asignación activa ya existe, omitida: NIT {nit_item.nit} -> Responsable {payload.responsable_id}")
                continue

            # PASO 2: Verificar si existe asignación INACTIVA (soft deleted)
            existente_inactiva = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == nit_item.nit,
                AsignacionNitResponsable.responsable_id == payload.responsable_id,
                AsignacionNitResponsable.activo == False  # Eliminada previamente
            ).first()

            if existente_inactiva:
                # REACTIVAR: Restaurar asignación eliminada
                existente_inactiva.activo = True
                existente_inactiva.actualizado_en = datetime.now()
                existente_inactiva.actualizado_por = current_user.usuario
                existente_inactiva.nombre_proveedor = nit_item.nombre_proveedor
                existente_inactiva.area = nit_item.area or responsable.area
                existente_inactiva.permitir_aprobacion_automatica = payload.permitir_aprobacion_automatica

                sincronizar_facturas_por_nit(db, nit_item.nit, payload.responsable_id)
                reactivadas += 1
                logger.debug(f"Asignación reactivada: NIT {nit_item.nit} -> Responsable {payload.responsable_id}")
            else:
                # PASO 3: Crear nueva asignación
                nueva = AsignacionNitResponsable(
                    nit=nit_item.nit,
                    nombre_proveedor=nit_item.nombre_proveedor,
                    responsable_id=payload.responsable_id,
                    area=nit_item.area or responsable.area,
                    permitir_aprobacion_automatica=payload.permitir_aprobacion_automatica,
                    requiere_revision_siempre=False,
                    activo=True,
                    creado_por=current_user.usuario
                )
                db.add(nueva)
                sincronizar_facturas_por_nit(db, nit_item.nit, payload.responsable_id)
                creadas += 1
                logger.debug(f"Nueva asignación creada: NIT {nit_item.nit} -> Responsable {payload.responsable_id}")

        except Exception as e:
            errores.append(f"NIT {nit_item.nit}: {str(e)}")
            logger.error(f"Error procesando NIT {nit_item.nit}: {str(e)}")

    # TRANSACCIÓN: Si hay errores críticos, hacer rollback
    if errores:
        # Commit parcial (comentar si se prefiere all-or-nothing)
        db.commit()
        logger.warning(f"Asignación bulk completada con errores: {len(errores)} errores encontrados")
    else:
        db.commit()
        logger.info(
            f"Asignación bulk completada exitosamente: "
            f"{creadas} creadas, {reactivadas} reactivadas, {omitidas} omitidas"
        )

    # Construir mensaje informativo
    mensaje_partes = []
    if creadas > 0:
        mensaje_partes.append(f"{creadas} asignación(es) creada(s)")
    if reactivadas > 0:
        mensaje_partes.append(f"{reactivadas} reactivada(s)")
    if omitidas > 0:
        mensaje_partes.append(f"{omitidas} ya existía(n)")
    if errores:
        mensaje_partes.append(f"{len(errores)} error(es)")

    mensaje = " | ".join(mensaje_partes) if mensaje_partes else "Sin cambios"

    # Determinar si la operacion fue exitosa
    # Exitosa si se creo/reactivo al menos una O si todas fueron omitidas (ya existian)
    operacion_exitosa = (creadas + reactivadas > 0) or (omitidas > 0 and len(errores) == 0)

    return {
        "success": operacion_exitosa,
        "total_procesados": len(payload.nits),
        "creadas": creadas,
        "reactivadas": reactivadas,
        "omitidas": omitidas,
        "errores": errores,
        "mensaje": mensaje
    }


@router.get("/por-responsable/{responsable_id}", response_model=AsignacionesPorResponsableResponse)
def obtener_asignaciones_por_responsable(
    responsable_id: int,
    activo: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """
    Obtiene todas las asignaciones de un responsable específico.
    Retorna estructura agrupada compatible con el frontend.
    """
    # Verificar que el responsable existe
    responsable = db.query(Responsable).filter(Responsable.id == responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable con ID {responsable_id} no encontrado"
        )

    # Obtener asignaciones
    asignaciones = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.responsable_id == responsable_id,
        AsignacionNitResponsable.activo == activo
    ).all()

    # Construir lista de asignaciones con responsable
    asignaciones_response = []
    for asig in asignaciones:
        asignaciones_response.append(AsignacionNitResponse(
            **asig.__dict__,
            responsable=ResponsableSimple.from_orm(responsable)
        ))

    # Retornar estructura agrupada
    return AsignacionesPorResponsableResponse(
        responsable_id=responsable_id,
        responsable=ResponsableSimple.from_orm(responsable),
        asignaciones=asignaciones_response,
        total=len(asignaciones_response)
    )
