"""
Servicio de Gestión de Proveedores - Enterprise Edition

Módulo centralizado para la creación y gestión de proveedores con soporte para:
- Búsqueda de proveedores existentes
- Auto-creación desde facturas
- Validación robusta de datos
- Auditoría completa
- Manejo de errores empresarial
- Logging estructurado

Arquitectura:
- Single Responsibility: Solo responsable de lógica de proveedores
- DRY: No hay código duplicado
- SOLID: Fácil de testear y extender
- Idempotente: Múltiples llamadas con mismos datos = mismo resultado

Autor: Equipo Senior de Desarrollo
Fecha: 2025-11-06
Nivel: Enterprise Fortune 500
"""

import logging
from typing import Tuple, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DatabaseError

from app.models.proveedor import Proveedor
from app.schemas.proveedor import ProveedorBase
from app.utils.nit_validator import NitValidator
from app.utils.normalizacion import normalizar_email, normalizar_razon_social
from app.crud.audit import create_audit

logger = logging.getLogger(__name__)


class ProviderManagementException(Exception):
    """Excepción base para errores de gestión de proveedores."""
    pass


class ProviderValidationException(ProviderManagementException):
    """Excepción para errores de validación de datos."""
    pass


class ProviderDatabaseException(ProviderManagementException):
    """Excepción para errores de base de datos."""
    pass


class ProviderManagementService:
    """
    Servicio centralizado para gestión de proveedores.

    Responsabilidades:
    1. Búsqueda de proveedores existentes
    2. Auto-creación desde facturas
    3. Validación de datos
    4. Normalización de datos
    5. Auditoría completa
    6. Manejo de errores robusto
    7. Logging estructurado

    Uso:
        service = ProviderManagementService(db_session)
        proveedor, fue_creado = service.get_or_create(
            nit="800123456",
            razon_social="EMPRESA XYZ S.A.S",
            email="contacto@xyz.com"
        )
    """

    def __init__(self, db: Session, created_by: str = "SISTEMA_AUTO_CREACION"):
        """
        Inicializa el servicio de gestión de proveedores.

        Args:
            db: Sesión de SQLAlchemy
            created_by: Usuario que crea (para auditoría)
        """
        self.db = db
        self.created_by = created_by

    # ================================================================================
    # BÚSQUEDA Y CREACIÓN
    # ================================================================================

    def get_or_create(
        self,
        nit: str,
        razon_social: Optional[str] = None,
        email: Optional[str] = None,
        telefono: Optional[str] = None,
        direccion: Optional[str] = None,
        area: Optional[str] = None,
        auto_create: bool = True,
    ) -> Tuple[Optional[Proveedor], bool]:
        """
        Busca un proveedor por NIT, crea si no existe (si auto_create=True).

        Patrón Idempotente:
        - Múltiples llamadas con los mismos datos siempre retornan el mismo proveedor
        - La segunda llamada no crea duplicado
        - Seguro para ejecutar en paralelo

        Args:
            nit: NIT del proveedor (en cualquier formato)
            razon_social: Razón social (requerido para auto-crear)
            email: Email (opcional)
            telefono: Teléfono (opcional)
            direccion: Dirección (opcional)
            area: Área (opcional)
            auto_create: Si False, retorna None si no existe

        Returns:
            Tuple[Proveedor, bool]: (proveedor_encontrado_o_creado, fue_creado)
            - proveedor: Instancia de Proveedor o None
            - fue_creado: True si se creó en esta llamada, False si ya existía

        Raises:
            ProviderValidationException: Si NIT o datos son inválidos
            ProviderDatabaseException: Si hay error en BD
        """
        # PASO 1: Validar y normalizar NIT
        try:
            nit_normalizado = self._validar_y_normalizar_nit(nit)
        except ProviderValidationException:
            raise

        # PASO 2: Buscar proveedor existente
        proveedor_existente = self._buscar_por_nit(nit_normalizado)
        if proveedor_existente:
            logger.debug(
                f"Proveedor encontrado existente",
                extra={
                    "proveedor_id": proveedor_existente.id,
                    "nit": nit_normalizado,
                    "origen": "MANUAL" if not proveedor_existente.es_auto_creado else "AUTO"
                }
            )
            return proveedor_existente, False

        # PASO 3: Decidir si crear
        if not auto_create:
            logger.info(
                f"Proveedor no encontrado y auto_create=False",
                extra={"nit": nit_normalizado}
            )
            return None, False

        # PASO 4: Crear nuevo proveedor
        try:
            proveedor_nuevo = self._crear_proveedor_automatico(
                nit_normalizado=nit_normalizado,
                razon_social=razon_social,
                email=email,
                telefono=telefono,
                direccion=direccion,
                area=area
            )
            logger.info(
                f"Proveedor auto-creado exitosamente",
                extra={
                    "proveedor_id": proveedor_nuevo.id,
                    "nit": nit_normalizado,
                    "razon_social": razon_social
                }
            )
            return proveedor_nuevo, True

        except Exception as e:
            logger.error(
                f"Error al auto-crear proveedor",
                extra={
                    "nit": nit_normalizado,
                    "razon_social": razon_social,
                    "error": str(e)
                },
                exc_info=True
            )
            raise ProviderDatabaseException(f"No se pudo crear proveedor: {str(e)}")

    def get_by_nit(self, nit: str, auto_normalize: bool = True) -> Optional[Proveedor]:
        """
        Obtiene un proveedor por NIT.

        Args:
            nit: NIT del proveedor
            auto_normalize: Si True, normaliza el NIT antes de buscar

        Returns:
            Proveedor o None
        """
        if auto_normalize:
            try:
                nit = self._validar_y_normalizar_nit(nit)
            except ProviderValidationException:
                return None

        return self._buscar_por_nit(nit)

    # ================================================================================
    # VALIDACIÓN Y NORMALIZACIÓN (PRIVADOS)
    # ================================================================================

    def _validar_y_normalizar_nit(self, nit: str) -> str:
        """
        Valida y normaliza un NIT usando NitValidator.

        Args:
            nit: NIT en cualquier formato

        Returns:
            NIT normalizado en formato XXXXXXXXX-D

        Raises:
            ProviderValidationException: Si NIT es inválido
        """
        if not nit or not isinstance(nit, str):
            raise ProviderValidationException("NIT debe ser una cadena no vacía")

        es_valido, nit_normalizado = NitValidator.validar_nit(nit.strip())

        if not es_valido:
            raise ProviderValidationException(
                f"NIT inválido: {nit}. Error: {nit_normalizado}"
            )

        logger.debug(
            f"NIT validado y normalizado",
            extra={"nit_original": nit, "nit_normalizado": nit_normalizado}
        )
        return nit_normalizado

    def _validar_razon_social(self, razon_social: Optional[str]) -> str:
        """
        Valida que la razón social sea válida.

        Args:
            razon_social: Razón social del proveedor

        Returns:
            Razón social normalizada

        Raises:
            ProviderValidationException: Si es inválida
        """
        if not razon_social:
            raise ProviderValidationException("Razón social es requerida para auto-crear")

        razon_social_norm = str(razon_social).strip()

        if len(razon_social_norm) < 3:
            raise ProviderValidationException(
                f"Razón social muy corta: '{razon_social_norm}' (mín 3 caracteres)"
            )

        if len(razon_social_norm) > 255:
            raise ProviderValidationException(
                f"Razón social muy larga: {len(razon_social_norm)} caracteres (máx 255)"
            )

        return normalizar_razon_social(razon_social_norm)

    def _validar_email(self, email: Optional[str]) -> Optional[str]:
        """
        Valida y normaliza un email (opcional).

        Args:
            email: Email del proveedor

        Returns:
            Email normalizado o None
        """
        if not email:
            return None

        try:
            return normalizar_email(email)
        except Exception as e:
            logger.warning(
                f"Email inválido, será ignorado",
                extra={"email": email, "error": str(e)}
            )
            return None

    # ================================================================================
    # OPERACIONES DE BASE DE DATOS (PRIVADOS)
    # ================================================================================

    def _buscar_por_nit(self, nit_normalizado: str) -> Optional[Proveedor]:
        """
        Busca un proveedor por NIT (ya normalizado).

        Args:
            nit_normalizado: NIT en formato XXXXXXXXX-D

        Returns:
            Proveedor o None

        Raises:
            ProviderDatabaseException: Si hay error en BD
        """
        try:
            return self.db.query(Proveedor).filter(
                Proveedor.nit == nit_normalizado
            ).first()

        except DatabaseError as e:
            logger.error(
                f"Error en base de datos al buscar proveedor",
                extra={"nit": nit_normalizado, "error": str(e)},
                exc_info=True
            )
            raise ProviderDatabaseException(f"Error buscando proveedor: {str(e)}")

    def _crear_proveedor_automatico(
        self,
        nit_normalizado: str,
        razon_social: Optional[str],
        email: Optional[str],
        telefono: Optional[str],
        direccion: Optional[str],
        area: Optional[str],
    ) -> Proveedor:
        """
        Crea un proveedor automáticamente desde factura (PRIVADO).

        Validaciones:
        - NIT: ya validado en get_or_create()
        - Razón social: requerida, mín 3 caracteres
        - Email: validado opcionalmente
        - Campos opcionales: aceptados como-están

        Args:
            nit_normalizado: NIT ya normalizado
            razon_social: Razón social (requerida)
            email: Email (opcional)
            telefono: Teléfono (opcional)
            direccion: Dirección (opcional)
            area: Área (opcional)

        Returns:
            Instancia de Proveedor creada en BD

        Raises:
            ProviderValidationException: Si datos son inválidos
            ProviderDatabaseException: Si hay error en BD
        """
        # VALIDACIÓN: Razón social
        razon_social_norm = self._validar_razon_social(razon_social)

        # VALIDACIÓN: Email (opcional)
        email_norm = self._validar_email(email)

        # CREAR: Instancia usando factory method
        proveedor = Proveedor.crear_automatico(
            nit=nit_normalizado,
            razon_social=razon_social_norm,
            email=email_norm,
            telefono=telefono,
            direccion=direccion,
            area=area
        )

        # GUARDAR: En BD
        try:
            self.db.add(proveedor)
            self.db.flush()  # Para obtener el ID sin commit
            self.db.commit()
            self.db.refresh(proveedor)

            logger.info(
                f"Proveedor guardado en BD",
                extra={
                    "proveedor_id": proveedor.id,
                    "nit": nit_normalizado,
                    "razon_social": razon_social_norm
                }
            )

        except IntegrityError as e:
            self.db.rollback()
            logger.error(
                f"Error de integridad al crear proveedor (posible duplicado)",
                extra={"nit": nit_normalizado, "error": str(e)},
                exc_info=True
            )
            raise ProviderDatabaseException(
                f"Error de integridad: {str(e)}. Posible NIT duplicado."
            )

        except DatabaseError as e:
            self.db.rollback()
            logger.error(
                f"Error en base de datos al crear proveedor",
                extra={"nit": nit_normalizado, "error": str(e)},
                exc_info=True
            )
            raise ProviderDatabaseException(f"Error en BD: {str(e)}")

        # AUDITORÍA: Registrar creación automática
        try:
            create_audit(
                db=self.db,
                tabla="proveedores",
                registro_id=proveedor.id,
                accion="crear_automatico",
                usuario=self.created_by,
                detalles={
                    "nit": nit_normalizado,
                    "razon_social": razon_social_norm,
                    "email": email_norm,
                    "telefono": telefono,
                    "direccion": direccion,
                    "area": area,
                    "motivo": "Auto-creación desde factura de invoice_extractor"
                }
            )
        except Exception as e:
            logger.warning(
                f"No se pudo registrar auditoría de creación",
                extra={"proveedor_id": proveedor.id, "error": str(e)}
            )
            # No falla la creación, solo log de warning

        return proveedor

    # ================================================================================
    # UTILIDADES
    # ================================================================================

    def buscar_auto_creados(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[list, int]:
        """
        Busca proveedores auto-creados (para auditoría/dashboard).

        Args:
            limit: Número máximo de resultados
            offset: Número de resultados a saltar

        Returns:
            Tuple[lista_proveedores, total_count]
        """
        try:
            query = self.db.query(Proveedor).filter(
                Proveedor.es_auto_creado == True
            )

            total = query.count()
            proveedores = query.order_by(
                Proveedor.creado_automaticamente_en.desc()
            ).offset(offset).limit(limit).all()

            return proveedores, total

        except DatabaseError as e:
            logger.error(
                f"Error buscando proveedores auto-creados",
                extra={"error": str(e)},
                exc_info=True
            )
            raise ProviderDatabaseException(f"Error en BD: {str(e)}")

    def obtener_estadisticas_auto_creacion(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de auto-creación para dashboard.

        Returns:
            Dict con:
            - total_auto_creados: Número total
            - fecha_primer_auto_creado: Timestamp
            - fecha_ultimo_auto_creado: Timestamp
            - total_todos: Total de proveedores
            - porcentaje: % de auto-creados
        """
        try:
            total_todos = self.db.query(Proveedor).count()
            total_auto_creados = self.db.query(Proveedor).filter(
                Proveedor.es_auto_creado == True
            ).count()

            # Obtener fechas extremas
            fecha_primer = self.db.query(
                Proveedor.creado_automaticamente_en
            ).filter(
                Proveedor.es_auto_creado == True
            ).order_by(Proveedor.creado_automaticamente_en.asc()).first()

            fecha_ultimo = self.db.query(
                Proveedor.creado_automaticamente_en
            ).filter(
                Proveedor.es_auto_creado == True
            ).order_by(Proveedor.creado_automaticamente_en.desc()).first()

            porcentaje = (total_auto_creados / total_todos * 100) if total_todos > 0 else 0

            return {
                "total_auto_creados": total_auto_creados,
                "total_proveedores": total_todos,
                "porcentaje_auto_creados": round(porcentaje, 2),
                "fecha_primer_auto_creado": fecha_primer[0] if fecha_primer else None,
                "fecha_ultimo_auto_creado": fecha_ultimo[0] if fecha_ultimo else None
            }

        except DatabaseError as e:
            logger.error(
                f"Error obteniendo estadísticas",
                extra={"error": str(e)},
                exc_info=True
            )
            raise ProviderDatabaseException(f"Error en BD: {str(e)}")
