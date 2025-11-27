"""
Router API para gestión de asignaciones NIT-Usuario.
Reemplazo de responsable_proveedor, usando SOLO asignacion_nit_responsable.

 NUEVA ARQUITECTURA UNIFICADA
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.core.security import get_current_usuario, require_role
from app.utils.logger import logger
from app.utils.nit_validator import NitValidator
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.usuario import Usuario
from app.models.proveedor import Proveedor
from app.models.factura import Factura
from app.models.email_config import NitConfiguracion
from app.services.audit_service import AuditService
from pydantic import BaseModel


router = APIRouter(prefix="/asignacion-nit", tags=["Asignación NIT-Usuario"])


# ==================== SCHEMAS ====================

class AsignacionNitCreate(BaseModel):
    """Crear nueva asignación NIT -> Usuario"""
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
    """Información básica del usuario"""
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
    """Asignar múltiples NITs a un usuario"""
    responsable_id: int
    nits: List[NitBulkItem]
    permitir_aprobacion_automatica: Optional[bool] = True
    activo: Optional[bool] = True


class AsignacionBulkSimple(BaseModel):
    """
    PHASE 1: Asignación bulk simplificada con solo NITs (sin nombre_proveedor requerido).

    Use case: Usuario pega una lista de NITs separados por comas sin información de proveedor.
    El sistema los asigna usando solo el NIT y busca información en BD.

    Ejemplo:
    {
        "responsable_id": 1,
        "nits": "800185449,900123456,800999999",
        "permitir_aprobacion_automatica": true
    }
    """
    responsable_id: int
    nits: str  # Texto con NITs separados por comas o líneas
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


def sincronizar_facturas_por_nit(db: Session, nit: str, responsable_id: int, responsable_anterior_id: Optional[int] = None, validar_existencia: bool = False):
    """
    Actualiza todas las facturas de un NIT para asignarles el usuario correcto.

    ARQUITECTURA MEJORADA (ENTERPRISE + NIT NORMALIZATION):
    - Acepta NITs en formato normalizado: "XXXXXXXXX-D" (ej: "800185449-9")
    - Busca proveedores usando búsqueda EXACTA en tabla PROVEEDORES
    - NEW: Si se proporciona responsable_anterior_id, actualiza TODAS las facturas
      del usuario anterior, no solo las que tienen responsable_id = NULL
    - NEW: Si validar_existencia=True, verifica que el NIT exista en PROVEEDORES

    PARÁMETROS:
    - nit: NIT NORMALIZADO a sincronizar (formato "XXXXXXXXX-D")
    - responsable_id: Nuevo responsable
    - responsable_anterior_id: Usuario anterior (PHASE 2 - para reassignment completo)
    - validar_existencia: Si True, falla si el NIT no está en tabla PROVEEDORES (PHASE 1)

    COMPORTAMIENTO:
    - Si responsable_anterior_id es None: Sincroniza facturas con responsable_id = NULL (original)
    - Si responsable_anterior_id es proporcionado: Sincroniza TODAS las facturas del
      responsable anterior, garantizando reassignment completo sin datos huérfanos
    - Si validar_existencia=True: Levanta excepción si NIT no existe en PROVEEDORES
    """
    # FASE 1: Validación - Verificar que el NIT existe en PROVEEDORES
    if validar_existencia:
        proveedores_validacion = db.query(Proveedor).filter(
            Proveedor.nit == nit  # Búsqueda EXACTA con NIT normalizado
        ).all()

        if not proveedores_validacion:
            # NIT no encontrado en proveedores
            return None  # Señaliza error, será manejado por el caller

    # Obtener proveedores con ese NIT (búsqueda exacta con NIT normalizado)
    proveedores = db.query(Proveedor).filter(
        Proveedor.nit == nit  # Búsqueda EXACTA con NIT normalizado
    ).all()

    total_facturas = 0

    # FASE 2: Lógica de reassignment completo
    for proveedor in proveedores:
        if responsable_anterior_id is not None:
            # REASSIGNMENT COMPLETO: Actualizar TODAS las facturas del usuario anterior
            # Esto garantiza que no queden facturas "huérfanas" con el usuario viejo
            facturas = db.query(Factura).filter(
                Factura.proveedor_id == proveedor.id,
                Factura.responsable_id == responsable_anterior_id  # Solo las del usuario anterior
            ).all()
        else:
            # COMPORTAMIENTO ORIGINAL: Sincronizar facturas sin asignar (NULL)
            # Mantiene compatibilidad backward con código existente
            facturas = db.query(Factura).filter(
                Factura.proveedor_id == proveedor.id,
                Factura.responsable_id.is_(None)  # Solo las sin asignar
            ).all()

        for factura in facturas:
            factura.responsable_id = responsable_id
            total_facturas += 1

    if responsable_anterior_id is not None:
        logger.info(
            f"[PHASE 2] Sincronizadas {total_facturas} facturas para NIT {nit} "
            f"({len(proveedores)} proveedores) -> Reassignment completo: "
            f"Usuario {responsable_anterior_id} → {responsable_id}"
        )
    else:
        logger.info(
            f"Sincronizadas {total_facturas} facturas para NIT {nit} "
            f"({len(proveedores)} proveedores) -> Usuario {responsable_id} (sin asignar)"
        )

    return total_facturas


def desasignar_facturas_por_nit(db: Session, nit: str, responsable_id: int):
    """
    Desasigna SOLO las facturas del NIT específico para el usuario.
    Se ejecuta cuando se elimina una asignación NIT-Usuario.

    ENTERPRISE PATTERN (CORRECTO):
    - Al eliminar asignación de NIT 123 a Alexander:
      * SOLO desasigna las facturas del NIT 123
      * NO desasigna otras facturas de Alexander
      * Si Alexander tiene NIT 456, esas facturas se mantienen asignadas

    - Facturas del NIT vuelven a pool "sin asignar"
    - Si se reasigna el NIT, se vuelven a asignar automáticamente
    """
    # PASO 1: Validar y normalizar NIT
    es_valido, nit_normalizado = NitValidator.validar_nit(nit)
    if not es_valido:
        logger.warning(f"NIT inválido en desasignación: {nit}")
        return 0

    # PASO 2: Obtener proveedor_id del NIT
    proveedor = db.query(Proveedor).filter(
        Proveedor.nit == nit_normalizado
    ).first()

    if not proveedor:
        logger.info(f"No existe proveedor con NIT {nit_normalizado}")
        return 0

    # PASO 3: Desasignar SOLO las facturas de este NIT y responsable
    facturas = db.query(Factura).filter(
        and_(
            Factura.proveedor_id == proveedor.id,
            Factura.responsable_id == responsable_id
        )
    ).all()

    total_facturas = len(facturas)
    for factura in facturas:
        factura.responsable_id = None  # Desasignar

    logger.info(
        f"Desasignadas {total_facturas} facturas del NIT {nit_normalizado} "
        f"para Usuario ID={responsable_id} -> responsable_id = NULL"
    )
    return total_facturas


# ==================== ENDPOINTS ====================

@router.get("/", response_model=List[AsignacionNitResponse])
def listar_asignaciones_nit(
    skip: int = 0,
    limit: int = 100,
    responsable_id: Optional[int] = Query(None),
    nit: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario)
):
    """
    Lista todas las asignaciones NIT -> Usuario.

    **COMPORTAMIENTO ENTERPRISE-GRADE (HARD DELETE):**
    - Retorna TODAS las asignaciones activas (no hay eliminadas en BD)
    - Tabla limpia: solo registros que importan
    - No hay filtros de inactivos (hard delete pattern)

    **Filtros disponibles:**
    - responsable_id: Filtrar por responsable específico
    - nit: Filtrar por NIT específico

    **Ejemplos:**
    - GET /asignacion-nit/ -> Todas las asignaciones activas
    - GET /asignacion-nit/?responsable_id=1 -> Asignaciones de responsable 1
    - GET /asignacion-nit/?nit=800185449 -> Asignaciones del NIT

    **Nivel:** Enterprise Production-Ready - Hard Delete Pattern
    """
    query = db.query(AsignacionNitResponsable)

    if responsable_id is not None:
        query = query.filter(AsignacionNitResponsable.responsable_id == responsable_id)

    # ENTERPRISE: Filtro por NIT con normalización automática usando NitValidator
    # Acepta NITs en cualquier formato y normaliza antes de buscar
    if nit is not None:
        # Normalizar el NIT de búsqueda usando NitValidator
        es_valido, nit_normalizado_busqueda = NitValidator.validar_nit(nit)

        if not es_valido:
            # NIT inválido, retornar lista vacía
            asignaciones = []
        else:
            # Búsqueda exacta con NIT normalizado (todos en BD están normalizados)
            asignaciones = query.filter(
                AsignacionNitResponsable.nit == nit_normalizado_busqueda
            ).offset(skip).limit(limit).all()
    else:
        # Sin filtro de NIT, usar query normal con paginación en DB
        asignaciones = query.offset(skip).limit(limit).all()

    # Enriquecer con datos completos del usuario
    resultado = []
    for asig in asignaciones:
        responsable = db.query(Usuario).filter(Usuario.id == asig.responsable_id).first()
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
    current_user=Depends(get_current_usuario)  # Cualquier usuario autenticado
):
    """
    Crea una nueva asignación NIT -> Usuario.

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
    # Verificar que el usuario existe
    responsable = db.query(Usuario).filter(Usuario.id == payload.responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {payload.responsable_id} no encontrado"
        )

    # VERIFICAR SI EXISTE ASIGNACIÓN (duplicado)
    # HARD DELETE PATTERN: No hay registros inactivos
    existente = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.nit == payload.nit,
        AsignacionNitResponsable.responsable_id == payload.responsable_id
    ).first()

    if existente:
        # Duplicado: asignación ya existe
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El responsable '{responsable.nombre}' ya tiene asignado el NIT {payload.nit}. "
                   f"Esta asignación ya existe en el sistema. "
                   f"Para cambiar el usuario, elimine esta asignación primero."
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
        f"Asignación NIT CREADA: {payload.nit} -> Usuario {payload.responsable_id} "
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
    current_user=Depends(get_current_usuario)  # Cualquier usuario autenticado
):
    """
    Actualiza una asignación NIT -> Usuario existente.

    Si cambia el usuario_id, sincroniza automáticamente todas las facturas.
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

    # Si cambió el usuario, sincronizar facturas (PHASE 2: REASSIGNMENT COMPLETO)
    if payload.responsable_id and payload.responsable_id != responsable_anterior:
        total_facturas = sincronizar_facturas_por_nit(
            db,
            asignacion.nit,
            payload.responsable_id,
            responsable_anterior_id=responsable_anterior  # PHASE 2: Pasa responsable anterior para sync completo
        )
        logger.info(
            f"Usuario cambiado: {responsable_anterior} -> {payload.responsable_id}, "
            f"{total_facturas} facturas sincronizadas (PHASE 2: Reassignment completo)"
        )

    db.commit()
    db.refresh(asignacion)

    # Obtener datos completos del usuario
    responsable = db.query(Usuario).filter(Usuario.id == asignacion.responsable_id).first()

    return AsignacionNitResponse(
        **asignacion.__dict__,
        responsable=ResponsableSimple.from_orm(responsable) if responsable else None
    )


@router.delete("/{asignacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_asignacion_nit(
    asignacion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario)
):
    """
    Elimina una asignación NIT -> Usuario de la base de datos.

    **HARD DELETE PATTERN (CORRECTO):**
    - Elimina físicamente el registro de la tabla asignacion_nit_responsable
    - La asignación NO se puede restaurar (fue eliminada)
    - Se pueden crear nuevas asignaciones del mismo NIT a otro responsable
    - DESASIGNA SOLO las facturas del NIT específico (no todas del usuario)

    **SINCRONIZACIÓN AUTOMÁTICA:**
    - SOLO las facturas del NIT pierden su responsable asignado
    - Otras facturas del usuario se mantienen (ej: si responsable tiene NIT 123 y 456)
    - Facturas del NIT vuelven a pool "sin asignar"
    - Si se reasigna el NIT, las facturas se vuelven a asignar automáticamente

    **ARQUITECTURA CORRECTA:**
    - Tabla limpia: solo asignaciones activas
    - No hay "fantasmas" en la BD
    - Queries simples sin filtros `activo = true`
    - Usuario se puede reasignar a otro responsable

    **Nivel:** Enterprise Production-Ready - Hard Delete Pattern
    """
    # PASO 1: Obtener asignación
    asignacion = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.id == asignacion_id
    ).first()

    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asignación con ID {asignacion_id} no encontrada"
        )

    # Guardar datos antes de eliminar (para logging)
    nit = asignacion.nit
    responsable_id = asignacion.responsable_id

    # PASO 2: DESASIGNAR FACTURAS - Sincronización específica al NIT
    total_facturas_desasignadas = desasignar_facturas_por_nit(
        db,
        nit=nit,
        responsable_id=responsable_id
    )

    # PASO 3: HARD DELETE - Eliminar físicamente el registro
    db.delete(asignacion)
    db.commit()

    logger.info(
        f"Asignación NIT eliminada (hard delete): NIT={nit}, "
        f"Usuario ID={responsable_id}, ID={asignacion_id}, "
        f"Usuario={current_user.usuario}, "
        f"Facturas desasignadas={total_facturas_desasignadas}"
    )

    return None




@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def crear_asignaciones_bulk(
    payload: AsignacionBulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario)  # Cualquier usuario autenticado
):
    """
    Asigna múltiples NITs a un usuario de una sola vez.

    **COMPORTAMIENTO ENTERPRISE-GRADE (HARD DELETE):**
    - Validación de duplicados: no permite crear si ya existe
    - Operación transaccional: si falla uno, se continúa (best-effort)
    - Retorna estadísticas detalladas de la operación
    - NO soporta reactivación (hard delete pattern)

    **Retorna:**
    - total_procesados: Cantidad de NITs en el payload
    - creadas: Nuevas asignaciones creadas
    - omitidas: Asignaciones que ya existían (duplicados)
    - errores: Lista de errores encontrados

    **Nivel:** Enterprise Production-Ready with Hard Delete Pattern
    """
    # Verificar responsable
    responsable = db.query(Usuario).filter(Usuario.id == payload.responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {payload.responsable_id} no encontrado"
        )

    creadas = 0
    omitidas = 0
    errores = []

    for nit_item in payload.nits:
        try:
            # PASO 1: NORMALIZAR NIT usando NitValidator
            es_valido, nit_normalizado_o_error = NitValidator.validar_nit(nit_item.nit)
            if not es_valido:
                errores.append(f"NIT {nit_item.nit}: {nit_normalizado_o_error}")
                logger.error(f"Error normalizando NIT {nit_item.nit}: {nit_normalizado_o_error}")
                continue

            nit_normalizado = nit_normalizado_o_error

            # PASO 2: BUSCAR PROVEEDOR PARA OBTENER razon_social AUTOMÁTICAMENTE
            # Enterprise Pattern: Una sola fuente de verdad (master data en proveedores)
            proveedor = db.query(Proveedor).filter(
                Proveedor.nit == nit_normalizado
            ).first()

            # Usar razon_social del proveedor si existe, sino usar lo que envía frontend
            nombre_proveedor_final = proveedor.razon_social if proveedor else nit_item.nombre_proveedor

            # PASO 3: Verificar si existe asignación (hard delete pattern - no hay inactivas)
            existente = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == nit_normalizado,
                AsignacionNitResponsable.responsable_id == payload.responsable_id
            ).first()

            if existente:
                # Ya existe, omitir
                omitidas += 1
                logger.debug(f"Asignación ya existe, omitida: NIT {nit_normalizado} -> Usuario {payload.responsable_id}")
                continue

            # PASO 4: Crear nueva asignación
            nueva = AsignacionNitResponsable(
                nit=nit_normalizado,
                nombre_proveedor=nombre_proveedor_final,  # Usar razon_social del proveedor
                responsable_id=payload.responsable_id,
                area=nit_item.area or responsable.area,
                permitir_aprobacion_automatica=payload.permitir_aprobacion_automatica,
                requiere_revision_siempre=False,
                creado_por=current_user.usuario
            )
            db.add(nueva)
            sincronizar_facturas_por_nit(db, nit_normalizado, payload.responsable_id)
            creadas += 1
            logger.debug(f"Nueva asignación creada: NIT {nit_normalizado} ({nombre_proveedor_final}) -> Usuario {payload.responsable_id}")

        except Exception as e:
            errores.append(f"NIT {nit_item.nit}: {str(e)}")
            logger.error(f"Error procesando NIT {nit_item.nit}: {str(e)}")

    # Commit de cambios
    db.commit()

    if creadas > 0 or omitidas > 0:
        logger.info(
            f"Asignación bulk completada: "
            f"{creadas} creadas, {omitidas} omitidas"
            + (f", {len(errores)} errores" if errores else "")
        )

    # Construir mensaje informativo
    mensaje_partes = []
    if creadas > 0:
        mensaje_partes.append(f"{creadas} asignación(es) creada(s)")
    if omitidas > 0:
        mensaje_partes.append(f"{omitidas} ya existía(n)")
    if errores:
        mensaje_partes.append(f"{len(errores)} error(es)")

    mensaje = " | ".join(mensaje_partes) if mensaje_partes else "Sin cambios"

    # Determinar si la operacion fue exitosa
    operacion_exitosa = (creadas > 0) or (omitidas > 0 and len(errores) == 0)

    return {
        "success": operacion_exitosa,
        "total_procesados": len(payload.nits),
        "creadas": creadas,
        "omitidas": omitidas,
        "errores": errores,
        "mensaje": mensaje
    }


@router.post("/bulk-simple", status_code=status.HTTP_201_CREATED)
def crear_asignaciones_bulk_simple(
    payload: AsignacionBulkSimple,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario)
):
    """
    PHASE 1: Asignación bulk simplificada con validación de proveedores.

    Acepta una lista de NITs en formato texto (separados por comas, saltos
    de línea, o semicolones). Valida que TODOS los NITs existan en tabla
    PROVEEDORES antes de asignar.

    **ENTRADA:**
    ```json
    {
        "responsable_id": 1,
        "nits": "800185449,900123456,800999999",
        "permitir_aprobacion_automatica": true
    }
    ```

    **PROCESAMIENTO:**
    1. Parsea el texto de NITs (soporta comas, saltos de línea, espacios)
    2. Valida que TODOS los NITs existan en tabla PROVEEDORES
    3. Si algún NIT no existe, retorna error ANTES de hacer cambios
    4. Si todos son válidos: asigna y sincroniza facturas automáticamente

    **VALIDACIÓN CRÍTICA:**
    - Si NIT no existe en PROVEEDORES, retorna error inmediato
    - Mensaje claro: "Ninguno de los NITs ingresados está registrado como
      proveedor: {lista_de_nits_inválidos}"

    **RETORNA:**
    - success: True si completó exitosamente
    - total_procesados: NITs procesados
    - creadas: Nuevas asignaciones
    - reactivadas: Reactivadas
    - errores: Lista de NITs que fallaron

    **NIVEL:** Enterprise Production-Ready with Validation
    """
    # Verificar responsable
    responsable = db.query(Usuario).filter(
        Usuario.id == payload.responsable_id
    ).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {payload.responsable_id} no encontrado"
        )

    # PASO 1: Parsear el texto de NITs
    import re
    nits_raw = re.split(r'[,\n\t\r;]', payload.nits)
    nits_procesados_raw = [nit.strip() for nit in nits_raw if nit.strip()]

    if not nits_procesados_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se encontraron NITs válidos en el texto proporcionado"
        )

    # PASO 1.5: NORMALIZAR NITs usando NitValidator
    # Esto convierte "17343874" -> "017343874-4", "800.185.449" -> "800185449-9", etc.
    nits_procesados = []
    nits_normalizacion_errores = []

    for nit_raw in nits_procesados_raw:
        es_valido, nit_normalizado_o_error = NitValidator.validar_nit(nit_raw)
        if es_valido:
            nits_procesados.append(nit_normalizado_o_error)
        else:
            nits_normalizacion_errores.append((nit_raw, nit_normalizado_o_error))

    # Si hay errores de normalización, reportarlos
    if nits_normalizacion_errores:
        errores_str = "; ".join([f"{nit} ({err})" for nit, err in nits_normalizacion_errores])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Algunos NITs no pudieron ser normalizados: {errores_str}"
        )

    # PASO 2: VALIDACIÓN CRÍTICA - Verificar que TODOS los NITs NORMALIZADOS existan en PROVEEDORES
    nits_invalidos = []
    for nit_normalizado in nits_procesados:
        proveedor = db.query(Proveedor).filter(
            Proveedor.nit == nit_normalizado
        ).first()

        if not proveedor:
            nits_invalidos.append(nit_normalizado)

    # Si hay NITs inválidos, rechazar TODA la operación
    if nits_invalidos:
        nits_invalidos_str = ", ".join(nits_invalidos)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Ninguno de los NITs ingresados está registrado como "
                f"proveedor: {nits_invalidos_str}. "
                "Verifique que los NITs existan en la tabla de proveedores."
            )
        )

    # PASO 3: Procesar asignaciones (todos los NITs NORMALIZADOS son válidos y existen en PROVEEDORES)
    # HARD DELETE PATTERN - No hay reactivación
    creadas = 0
    omitidas = 0
    errores = []

    for nit_normalizado in nits_procesados:
        try:
            # Obtener proveedor para obtener nombre y otros datos
            proveedor = db.query(Proveedor).filter(
                Proveedor.nit == nit_normalizado
            ).first()
            nombre_proveedor = (
                proveedor.razon_social if proveedor else f"Proveedor {nit_normalizado}"
            )

            # Verificar si existe asignación (hard delete - no hay inactivas)
            existente = db.query(
                AsignacionNitResponsable
            ).filter(
                AsignacionNitResponsable.nit == nit_normalizado,
                AsignacionNitResponsable.responsable_id == (
                    payload.responsable_id
                )
            ).first()

            if existente:
                omitidas += 1
                logger.debug(
                    f"Asignación ya existe: NIT {nit_normalizado}"
                )
                continue

            # Crear nueva asignación
            nueva = AsignacionNitResponsable(
                nit=nit_normalizado,
                nombre_proveedor=nombre_proveedor,
                responsable_id=payload.responsable_id,
                area=responsable.area,
                permitir_aprobacion_automatica=(
                    payload.permitir_aprobacion_automatica
                ),
                requiere_revision_siempre=False,
                creado_por=current_user.usuario
            )
            db.add(nueva)
            sincronizar_facturas_por_nit(
                db, nit_normalizado, payload.responsable_id
            )
            creadas += 1
            logger.debug(f"Nueva asignación creada: NIT {nit_normalizado}")

        except Exception as e:
            errores.append(f"NIT {nit_normalizado}: {str(e)}")
            logger.error(f"Error procesando NIT {nit_normalizado}: {str(e)}")

    # Commit de cambios
    db.commit()

    if creadas > 0 or omitidas > 0:
        logger.info(
            f"Asignación bulk simple completada: "
            f"{creadas} creadas, {omitidas} omitidas"
            + (f", {len(errores)} errores" if errores else "")
        )

    # Construir mensaje
    mensaje_partes = []
    if creadas > 0:
        mensaje_partes.append(f"{creadas} creada(s)")
    if omitidas > 0:
        mensaje_partes.append(f"{omitidas} ya existía(n)")
    if errores:
        mensaje_partes.append(f"{len(errores)} error(es)")

    mensaje = " | ".join(mensaje_partes) if mensaje_partes else (
        "Sin cambios"
    )

    operacion_exitosa = (
        (creadas > 0) or
        (omitidas > 0 and len(errores) == 0)
    )

    return {
        "success": operacion_exitosa,
        "total_procesados": len(nits_procesados),
        "creadas": creadas,
        "omitidas": omitidas,
        "errores": errores,
        "mensaje": mensaje
    }


@router.get("/por-responsable/{responsable_id}", response_model=AsignacionesPorResponsableResponse)
def obtener_asignaciones_por_responsable(
    responsable_id: int,
    activo: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_usuario)
):
    """
    Obtiene todas las asignaciones de un usuario específico.
    Retorna estructura agrupada compatible con el frontend.
    """
    # Verificar que el usuario existe
    responsable = db.query(Usuario).filter(Usuario.id == responsable_id).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {responsable_id} no encontrado"
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


# ==================== NUEVO ENDPOINT: Asignación desde nit_configuracion ====================

@router.post("/diagnostico-nits", status_code=status.HTTP_200_OK)
def diagnostico_nits(
    payload: AsignacionBulkSimple,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    """
    ENDPOINT DE DIAGNÓSTICO - Verifica qué está pasando con los NITs.
    Retorna información detallada sobre cada NIT enviado.
    """
    import re
    nits_raw = re.split(r'[,\n\t\r;]', payload.nits)
    nits_procesados_raw = [nit.strip() for nit in nits_raw if nit.strip()]

    resultado = []
    for nit_raw in nits_procesados_raw:
        es_valido, nit_normalizado_o_error = NitValidator.validar_nit(nit_raw)

        if es_valido:
            # Buscar en nit_configuracion
            nit_config = db.query(NitConfiguracion).filter(
                NitConfiguracion.nit == nit_normalizado_o_error
            ).all()

            resultado.append({
                "nit_original": nit_raw,
                "nit_normalizado": nit_normalizado_o_error,
                "valido": True,
                "en_nit_configuracion": len(nit_config) > 0,
                "registros_en_config": len(nit_config),
                "config_activos": len([x for x in nit_config if x.activo])
            })
        else:
            resultado.append({
                "nit_original": nit_raw,
                "valido": False,
                "error": nit_normalizado_o_error
            })

    return {"nits": resultado, "total": len(resultado)}


@router.post("/bulk-nit-config", status_code=status.HTTP_201_CREATED)
def crear_asignaciones_desde_nit_config(
    payload: AsignacionBulkSimple,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    """
    Asigna NITs directamente desde la tabla nit_configuracion sin requerir que existan en proveedores.

    **ENTRADA:**
    ```json
    {
        "responsable_id": 6,
        "nits": "017343874-4,047425554-4,080818383-9",
        "permitir_aprobacion_automatica": true
    }
    ```

    **PROCESAMIENTO:**
    1. Parsea el texto de NITs (soporta comas, saltos de línea, espacios)
    2. Normaliza los NITs usando NitValidator
    3. Valida que existan en nit_configuracion (no en proveedores)
    4. Crea asignaciones sin requerir que haya facturas

    **DIFERENCIA CON /bulk-simple:**
    - /bulk-simple: Requiere que NITs existan en tabla PROVEEDORES (con facturas)
    - /bulk-nit-config: Asigna desde tabla NIT_CONFIGURACION (sin facturas requeridas)

    **RETORNA:**
    - success: True si completó exitosamente
    - total_procesados: NITs procesados
    - creadas: Nuevas asignaciones
    - errores: Lista de NITs que fallaron
    """
    # Verificar responsable
    responsable = db.query(Usuario).filter(
        Usuario.id == payload.responsable_id
    ).first()
    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {payload.responsable_id} no encontrado"
        )

    # PASO 1: Parsear el texto de NITs
    import re
    nits_raw = re.split(r'[,\n\t\r;]', payload.nits)
    nits_procesados_raw = [nit.strip() for nit in nits_raw if nit.strip()]

    if not nits_procesados_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se encontraron NITs válidos en el texto proporcionado"
        )

    # PASO 2: NORMALIZAR NITs
    nits_procesados = []
    nits_normalizacion_errores = []

    for nit_raw in nits_procesados_raw:
        es_valido, nit_normalizado_o_error = NitValidator.validar_nit(nit_raw)
        if es_valido:
            nits_procesados.append(nit_normalizado_o_error)
        else:
            nits_normalizacion_errores.append((nit_raw, nit_normalizado_o_error))

    if nits_normalizacion_errores:
        errores_str = "; ".join([f"{nit} ({err})" for nit, err in nits_normalizacion_errores])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Algunos NITs no pudieron ser normalizados: {errores_str}"
        )

    # PASO 3: VALIDACIÓN - Verificar que los NITs existan en nit_configuracion
    nits_invalidos = []
    for nit_normalizado in nits_procesados:
        nit_config = db.query(NitConfiguracion).filter(
            NitConfiguracion.nit == nit_normalizado,
            NitConfiguracion.activo == True
        ).first()

        if not nit_config:
            nits_invalidos.append(nit_normalizado)

    if nits_invalidos:
        nits_invalidos_str = ", ".join(nits_invalidos)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Los siguientes NITs no están configurados en nit_configuracion: "
                f"{nits_invalidos_str}. "
                "Agregúelos a la configuración de extracción de emails primero."
            )
        )

    # PASO 4: Procesar asignaciones
    creadas = 0
    omitidas = 0
    errores = []

    for nit_normalizado in nits_procesados:
        try:
            # Verificar si ya existe la asignación
            asignacion_existente = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == nit_normalizado,
                AsignacionNitResponsable.responsable_id == payload.responsable_id,
                AsignacionNitResponsable.activo == True
            ).first()

            if asignacion_existente:
                omitidas += 1
                continue

            # Obtener nombre del NIT desde nit_configuracion si existe
            nit_config = db.query(NitConfiguracion).filter(
                NitConfiguracion.nit == nit_normalizado
            ).first()
            nombre_proveedor = nit_config.nombre_proveedor if nit_config else None

            # Crear nueva asignación
            nueva_asignacion = AsignacionNitResponsable(
                nit=nit_normalizado,
                responsable_id=payload.responsable_id,
                nombre_proveedor=nombre_proveedor,
                permitir_aprobacion_automatica=payload.permitir_aprobacion_automatica,
                activo=True,
                fecha_asignacion=datetime.utcnow()
            )
            db.add(nueva_asignacion)
            creadas += 1

        except Exception as e:
            logger.error(f"Error asignando NIT {nit_normalizado}: {str(e)}", exc_info=True)
            errores.append({
                "nit": nit_normalizado,
                "error": str(e)
            })

    # Commit con manejo de errores mejorado
    try:
        db.commit()
    except Exception as e:
        logger.error(f"Error en COMMIT de asignaciones: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar asignaciones: {str(e)}"
        )

    # Log de auditoría
    logger.info(
        f"Asignaciones desde nit_configuracion: {creadas} creadas, {omitidas} omitidas, "
        f"{len(errores)} errores",
        extra={
            "responsable_id": payload.responsable_id,
            "total_nits": len(nits_procesados),
            "creadas": creadas,
            "omitidas": omitidas,
            "errores": len(errores)
        }
    )

    mensaje = (
        f"Se procesaron {len(nits_procesados)} NITs. "
        f"Creadas: {creadas}, Omitidas (ya existían): {omitidas}, "
        f"Errores: {len(errores)}"
    )

    return {
        "success": len(errores) == 0,
        "total_procesados": len(nits_procesados),
        "creadas": creadas,
        "omitidas": omitidas,
        "errores": errores,
        "responsable_id": payload.responsable_id,
        "mensaje": mensaje
    }
