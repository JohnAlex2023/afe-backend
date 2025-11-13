# app/crud/proveedor.py
"""
CRUD de Proveedores - Enterprise Edition

Módulo de acceso a datos para proveedores.

Arquitectura:
- Utiliza ProviderManagementService para lógica centralizada (DRY)
- Funciones públicas delgadas que coordinan operaciones
- Delegación de validación y normalización al servicio
- Transacciones controladas correctamente

Cambios principales:
- Nuevo: get_or_create_proveedor() para auto-creación
- Refactorizado: create_proveedor() usa ProviderManagementService
- Refactorizado: update_proveedor() usa ProviderManagementService
- Mantenido: Compatibilidad backwards con código existente

Autor: Equipo Senior de Desarrollo
Fecha: 2025-11-06
Nivel: Enterprise Fortune 500
"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.proveedor import Proveedor
from app.schemas.proveedor import ProveedorBase
from app.utils.nit_validator import NitValidator
from app.utils.normalizacion import normalizar_email, normalizar_razon_social
from app.services.provider_management import (
    ProviderManagementService,
    ProviderManagementException,
    ProviderValidationException
)

logger = logging.getLogger(__name__)


# ================================================================================
# OPERACIONES BÁSICAS (Sin cambios - backward compatible)
# ================================================================================

def get_proveedor(db: Session, proveedor_id: int) -> Optional[Proveedor]:
    """
    Obtiene un proveedor por ID.

    Args:
        db: Sesión de base de datos
        proveedor_id: ID del proveedor

    Returns:
        Proveedor o None
    """
    return db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()


def list_proveedores(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    solo_auto_creados: bool = False
) -> List[Proveedor]:
    """
    Lista proveedores con filtros opcionales.

    Args:
        db: Sesión de base de datos
        skip: Offset para paginación
        limit: Límite de resultados
        solo_auto_creados: Si True, solo devuelve proveedores auto-creados

    Returns:
        Lista de proveedores
    """
    query = db.query(Proveedor)

    if solo_auto_creados:
        query = query.filter(Proveedor.es_auto_creado == True)

    return query.offset(skip).limit(limit).all()


def get_proveedor_by_nit(db: Session, nit: str) -> Optional[Proveedor]:
    """
    Obtiene un proveedor por NIT (normaliza automáticamente).

    Args:
        db: Sesión de base de datos
        nit: NIT en cualquier formato

    Returns:
        Proveedor o None
    """
    try:
        service = ProviderManagementService(db)
        return service.get_by_nit(nit, auto_normalize=True)
    except ProviderManagementException as e:
        logger.error(f"Error obteniendo proveedor por NIT: {str(e)}")
        return None


# ================================================================================
# CREACIÓN DE PROVEEDORES
# ================================================================================

def create_proveedor(db: Session, data: ProveedorBase) -> Proveedor:
    """
    Crea un proveedor MANUALMENTE (desde API/UI).

    Este es el flujo tradicional donde un usuario admin crea el proveedor.
    Los datos se normalizan y validan antes de guardar.

    Args:
        db: Sesión de base de datos
        data: Schema ProveedorBase con datos del proveedor

    Returns:
        Proveedor creado

    Raises:
        ProviderValidationException: Si NIT es inválido
        ProviderDatabaseException: Si hay error en BD
    """
    logger.info(
        f"Creando proveedor MANUAL",
        extra={"nit": data.nit, "razon_social": data.razon_social}
    )

    # Delegar al servicio para validación y normalización centralizada
    service = ProviderManagementService(db, created_by="USUARIO_MANUAL")

    # Extraer datos del schema
    data_dict = data.dict()

    # Usar el servicio para normalizar y buscar/crear
    proveedor, fue_creado = service.get_or_create(
        nit=data_dict.get('nit'),
        razon_social=data_dict.get('razon_social'),
        email=data_dict.get('contacto_email'),
        telefono=data_dict.get('telefono'),
        direccion=data_dict.get('direccion'),
        area=data_dict.get('area'),
        auto_create=True
    )

    # IMPORTANTE: Si fue creado automáticamente, marcar como manual
    if fue_creado:
        proveedor.es_auto_creado = False  # Fue creado por usuario manual
        proveedor.creado_automaticamente_en = None
        db.commit()
        db.refresh(proveedor)

        logger.info(
            f"Proveedor MANUAL creado exitosamente",
            extra={"proveedor_id": proveedor.id, "nit": proveedor.nit}
        )

    return proveedor


def get_or_create_proveedor(
    db: Session,
    nit: str,
    razon_social: Optional[str] = None,
    email: Optional[str] = None,
    telefono: Optional[str] = None,
    direccion: Optional[str] = None,
    area: Optional[str] = None,
    auto_create: bool = True,
    created_by: str = "SISTEMA_AUTO_CREACION"
) -> Tuple[Optional[Proveedor], bool]:
    """
    Búsqueda o creación de proveedor (PATRÓN IDEMPOTENTE).

    Este es el punto de entrada principal para auto-creación desde facturas.

    Patrón Idempotente:
    - Primera llamada: Crea si no existe
    - Segunda llamada con mismos datos: Retorna el existente sin crear duplicado
    - Seguro para ejecutar en paralelo

    Args:
        db: Sesión de base de datos
        nit: NIT del proveedor (se normaliza automáticamente)
        razon_social: Razón social (requerida para auto-crear)
        email: Email (opcional)
        telefono: Teléfono (opcional)
        direccion: Dirección (opcional)
        area: Área (opcional)
        auto_create: Si False, retorna None si no existe
        created_by: Usuario que causa la creación (para auditoría)

    Returns:
        Tuple[Proveedor, bool]: (proveedor, fue_creado)

    Raises:
        ProviderValidationException: Si NIT o datos son inválidos
        ProviderDatabaseException: Si hay error en BD

    Ejemplo:
        proveedor, fue_creado = get_or_create_proveedor(
            db=session,
            nit="800123456",
            razon_social="EMPRESA XYZ S.A.S",
            email="contacto@xyz.com"
        )
        if fue_creado:
            print(f"Nuevo proveedor creado: {proveedor.id}")
        else:
            print(f"Proveedor encontrado: {proveedor.id}")
    """
    service = ProviderManagementService(db, created_by=created_by)

    return service.get_or_create(
        nit=nit,
        razon_social=razon_social,
        email=email,
        telefono=telefono,
        direccion=direccion,
        area=area,
        auto_create=auto_create
    )


# ================================================================================
# ACTUALIZACIÓN
# ================================================================================

def update_proveedor(
    db: Session,
    proveedor_id: int,
    data: ProveedorBase
) -> Optional[Proveedor]:
    """
    Actualiza un proveedor existente.

    Args:
        db: Sesión de base de datos
        proveedor_id: ID del proveedor a actualizar
        data: Schema ProveedorBase con nuevos datos

    Returns:
        Proveedor actualizado o None

    Raises:
        ProviderValidationException: Si datos son inválidos
        ProviderDatabaseException: Si hay error en BD
    """
    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not proveedor:
        return None

    logger.info(
        f"Actualizando proveedor",
        extra={"proveedor_id": proveedor_id, "nit": proveedor.nit}
    )

    service = ProviderManagementService(db, created_by="USUARIO_MANUAL")

    # Normalizar datos antes de actualizar
    data_dict = data.dict(exclude_unset=True)

    if 'nit' in data_dict and data_dict['nit']:
        # Validar y normalizar NIT
        try:
            es_valido, nit_normalizado = NitValidator.validar_nit(data_dict['nit'])
            if es_valido:
                data_dict['nit'] = nit_normalizado
            else:
                raise ProviderValidationException(f"NIT inválido: {data_dict['nit']}")
        except ProviderValidationException:
            raise

    if 'contacto_email' in data_dict and data_dict['contacto_email']:
        data_dict['contacto_email'] = normalizar_email(data_dict['contacto_email'])

    if 'razon_social' in data_dict and data_dict['razon_social']:
        data_dict['razon_social'] = normalizar_razon_social(data_dict['razon_social'])

    # Aplicar cambios
    for key, value in data_dict.items():
        setattr(proveedor, key, value)

    db.commit()
    db.refresh(proveedor)

    logger.info(
        f"Proveedor actualizado exitosamente",
        extra={"proveedor_id": proveedor_id}
    )

    return proveedor


# ================================================================================
# ELIMINACIÓN
# ================================================================================

def delete_proveedor(db: Session, proveedor_id: int) -> bool:
    """
    Elimina un proveedor.

    NOTA: Considera usar soft-delete en producción para auditoría.

    Args:
        db: Sesión de base de datos
        proveedor_id: ID del proveedor a eliminar

    Returns:
        True si se eliminó, False si no existe
    """
    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not proveedor:
        return False

    logger.warning(
        f"Eliminando proveedor",
        extra={"proveedor_id": proveedor_id, "nit": proveedor.nit}
    )

    db.delete(proveedor)
    db.commit()

    logger.info(f"Proveedor eliminado: {proveedor_id}")

    return True


# ================================================================================
# UTILIDADES PARA AUDITORÍA Y REPORTING
# ================================================================================

def get_stats_auto_creados(db: Session) -> dict:
    """
    Obtiene estadísticas de proveedores auto-creados.

    Returns:
        Dict con estadísticas
    """
    service = ProviderManagementService(db)
    return service.obtener_estadisticas_auto_creacion()


def count_proveedores_auto_creados(db: Session) -> int:
    """Cuenta el total de proveedores auto-creados."""
    return db.query(Proveedor).filter(Proveedor.es_auto_creado == True).count()


def count_proveedores_manuales(db: Session) -> int:
    """Cuenta el total de proveedores creados manualmente."""
    return db.query(Proveedor).filter(Proveedor.es_auto_creado == False).count()
