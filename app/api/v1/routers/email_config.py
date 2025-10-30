# app/api/v1/routers/email_config.py
"""
Endpoints REST para gestión de configuración de extracción de correos.

CRUD completo para cuentas de correo, NITs y consulta de historial.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.core.security import get_current_responsable, require_role
from app.schemas.email_config import (
    CuentaCorreoCreate,
    CuentaCorreoUpdate,
    CuentaCorreoResponse,
    CuentaCorreoSummary,
    NitConfiguracionCreate,
    NitConfiguracionUpdate,
    NitConfiguracionResponse,
    HistorialExtraccionResponse,
    ConfiguracionExtractorResponse,
    ConfiguracionExtractorEmail,
    BulkNitsCreate,
    BulkNitsResponse,
    EstadisticasExtraccion,
    NitValidationRequest,
    NitValidationResponse,
)
from app.crud import email_config as crud
from app.utils.nit_validator import NitValidator
from datetime import datetime

router = APIRouter(prefix="/email-config", tags=["Email Configuration"])


# ==================== Endpoints Cuenta Correo ====================

@router.get("/cuentas", response_model=List[CuentaCorreoSummary])
def listar_cuentas_correo(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    solo_activas: bool = Query(False),
    organizacion: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """
    Lista todas las cuentas de correo configuradas.

    **Filtros:**
    - `solo_activas`: Solo cuentas activas
    - `organizacion`: Filtrar por organización
    """
    resumen = crud.get_resumen_todas_cuentas(db)

    # Aplicar filtros
    if solo_activas:
        resumen = [c for c in resumen if c["activa"]]
    if organizacion:
        resumen = [c for c in resumen if c.get("organizacion") == organizacion]

    # Paginación
    resumen = resumen[skip : skip + limit]

    return resumen


@router.get("/cuentas/{cuenta_id}", response_model=CuentaCorreoResponse)
def obtener_cuenta_correo(
    cuenta_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """Obtiene detalles completos de una cuenta de correo incluyendo todos sus NITs."""
    cuenta = crud.get_cuenta_correo(db, cuenta_id)
    if not cuenta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta de correo con ID {cuenta_id} no encontrada"
        )
    return cuenta


@router.post("/cuentas", response_model=CuentaCorreoResponse, status_code=status.HTTP_201_CREATED)
def crear_cuenta_correo(
    cuenta: CuentaCorreoCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """
    Crea una nueva cuenta de correo para extracción.

    **Validaciones:**
    - El email debe ser único
    - NITs deben ser válidos (solo números)
    - No se permiten NITs duplicados en la lista inicial
    """
    # Verificar que el email no exista
    existing = crud.get_cuenta_correo_by_email(db, cuenta.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una cuenta con el email {cuenta.email}"
        )

    # Usar el username del usuario autenticado si no se proporciona creada_por
    if not cuenta.creada_por:
        cuenta.creada_por = current_user.usuario

    return crud.create_cuenta_correo(db, cuenta)


@router.put("/cuentas/{cuenta_id}", response_model=CuentaCorreoResponse)
def actualizar_cuenta_correo(
    cuenta_id: int,
    update_data: CuentaCorreoUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """Actualiza configuración de una cuenta de correo."""
    # Usar el username del usuario autenticado
    if not update_data.actualizada_por:
        update_data.actualizada_por = current_user.usuario

    cuenta = crud.update_cuenta_correo(db, cuenta_id, update_data)
    if not cuenta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta de correo con ID {cuenta_id} no encontrada"
        )
    return cuenta


@router.delete("/cuentas/{cuenta_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cuenta_correo(
    cuenta_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """
    Elimina una cuenta de correo y todos sus NITs asociados.

    **ADVERTENCIA:** Esta operación es irreversible.
    """
    success = crud.delete_cuenta_correo(db, cuenta_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta de correo con ID {cuenta_id} no encontrada"
        )


@router.post("/cuentas/{cuenta_id}/toggle-activa", response_model=CuentaCorreoResponse)
def toggle_cuenta_activa(
    cuenta_id: int,
    activa: bool = Query(..., description="True para activar, False para desactivar"),
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """Activa o desactiva una cuenta de correo."""
    cuenta = crud.toggle_cuenta_activa(db, cuenta_id, activa, current_user.usuario)
    if not cuenta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta de correo con ID {cuenta_id} no encontrada"
        )
    return cuenta


# ==================== Endpoints NIT Configuración ====================

@router.get("/nits/cuenta/{cuenta_id}", response_model=List[NitConfiguracionResponse])
def listar_nits_por_cuenta(
    cuenta_id: int,
    solo_activos: bool = Query(False),
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """Lista todos los NITs configurados en una cuenta."""
    # Verificar que la cuenta existe
    cuenta = crud.get_cuenta_correo(db, cuenta_id)
    if not cuenta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta de correo con ID {cuenta_id} no encontrada"
        )

    return crud.get_nits_by_cuenta(db, cuenta_id, solo_activos)


@router.post("/nits", response_model=NitConfiguracionResponse, status_code=status.HTTP_201_CREATED)
def crear_nit(
    nit: NitConfiguracionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """
    Agrega un nuevo NIT a una cuenta de correo.

    **Validaciones:**
    - La cuenta debe existir
    - El NIT no puede estar duplicado en la misma cuenta
    - El NIT debe ser válido (solo números, 5-20 dígitos)
    """
    # Verificar que la cuenta existe
    cuenta = crud.get_cuenta_correo(db, nit.cuenta_correo_id)
    if not cuenta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta de correo con ID {nit.cuenta_correo_id} no encontrada"
        )

    # Verificar duplicado
    existing = crud.get_nit_by_cuenta_and_nit(db, nit.cuenta_correo_id, nit.nit)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El NIT {nit.nit} ya está configurado en esta cuenta"
        )

    # Usar el username del usuario autenticado
    if not nit.creado_por:
        nit.creado_por = current_user.usuario

    return crud.create_nit_configuracion(db, nit)


@router.post("/nits/bulk", response_model=BulkNitsResponse)
def crear_nits_bulk(
    bulk_data: BulkNitsCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """
    Agrega múltiples NITs a una cuenta con NORMALIZACIÓN AUTOMÁTICA.

    **NORMALIZACIÓN AUTOMÁTICA:**
    - Acepta NITs en cualquier formato: "800185449", "800.185.449", "800185449-9", etc.
    - Calcula automáticamente el dígito verificador DIAN usando algoritmo módulo 11
    - Almacena todos los NITs en formato normalizado: "XXXXXXXXX-D"
    - Reporta errores de validación para NITs inválidos

    **Manejo de duplicados:**
    - Los NITs duplicados se ignoran y se reportan
    - La operación es atómica: se agregan todos los NITs válidos no duplicados
    - Valida que cada NIT sea correcto antes de almacenar
    """
    # Verificar que la cuenta existe
    cuenta = crud.get_cuenta_correo(db, bulk_data.cuenta_correo_id)
    if not cuenta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta de correo con ID {bulk_data.cuenta_correo_id} no encontrada"
        )

    # Usar el username del usuario autenticado
    if not bulk_data.creado_por:
        bulk_data.creado_por = current_user.usuario

    agregados, duplicados, detalles = crud.bulk_create_nits(
        db,
        bulk_data.cuenta_correo_id,
        bulk_data.nits,
        bulk_data.creado_por
    )

    # Calcular fallidos desde los detalles
    fallidos = sum(1 for d in detalles if d["status"] == "error")

    return BulkNitsResponse(
        cuenta_correo_id=bulk_data.cuenta_correo_id,
        nits_agregados=agregados,
        nits_duplicados=duplicados,
        nits_fallidos=fallidos,
        detalles=detalles,
    )


@router.post("/validate-nit", response_model=NitValidationResponse)
def validar_nit(
    request: NitValidationRequest,
    db: Session = Depends(get_db),
):
    """
    Valida un NIT y retorna su formato normalizado.

    **Descripción:**
    - Acepta NITs en cualquier formato: "800185449", "800.185.449", "800185449-9"
    - Calcula automáticamente el dígito verificador DIAN
    - Retorna el NIT normalizado: "XXXXXXXXX-D"
    - Si el NIT es inválido, retorna error descriptivo

    **Casos de uso:**
    - Validación en tiempo real desde el frontend
    - Normalización antes de almacenamiento
    - Verificación de dígito verificador

    **Ejemplo de request:**
    ```json
    {
      "nit": "800185449"
    }
    ```

    **Ejemplo de response (válido):**
    ```json
    {
      "is_valid": true,
      "nit_normalizado": "800185449-9",
      "error": null
    }
    ```

    **Ejemplo de response (inválido):**
    ```json
    {
      "is_valid": false,
      "nit_normalizado": null,
      "error": "NIT debe contener solo dígitos..."
    }
    ```
    """
    try:
        # Normalizar usando el validador oficial
        nit_normalizado = NitValidator.normalizar_nit(request.nit)
        return NitValidationResponse(
            is_valid=True,
            nit_normalizado=nit_normalizado,
            error=None
        )
    except ValueError as e:
        return NitValidationResponse(
            is_valid=False,
            nit_normalizado=None,
            error=str(e)
        )


@router.put("/nits/{nit_id}", response_model=NitConfiguracionResponse)
def actualizar_nit(
    nit_id: int,
    update_data: NitConfiguracionUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """Actualiza información de un NIT."""
    # Usar el username del usuario autenticado
    if not update_data.actualizado_por:
        update_data.actualizado_por = current_user.usuario

    nit = crud.update_nit_configuracion(db, nit_id, update_data)
    if not nit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NIT con ID {nit_id} no encontrado"
        )
    return nit


@router.delete("/nits/{nit_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_nit(
    nit_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """Elimina un NIT de una cuenta."""
    success = crud.delete_nit_configuracion(db, nit_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NIT con ID {nit_id} no encontrado"
        )


@router.post("/nits/{nit_id}/toggle-activo", response_model=NitConfiguracionResponse)
def toggle_nit_activo(
    nit_id: int,
    activo: bool = Query(..., description="True para activar, False para desactivar"),
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """Activa o desactiva un NIT."""
    nit = crud.toggle_nit_activo(db, nit_id, activo, current_user.usuario)
    if not nit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NIT con ID {nit_id} no encontrado"
        )
    return nit


# ==================== Endpoints Historial y Estadísticas ====================

@router.get("/historial/cuenta/{cuenta_id}", response_model=List[HistorialExtraccionResponse])
def obtener_historial_extraccion(
    cuenta_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """Obtiene historial de extracciones de una cuenta."""
    # Verificar que la cuenta existe
    cuenta = crud.get_cuenta_correo(db, cuenta_id)
    if not cuenta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta de correo con ID {cuenta_id} no encontrada"
        )

    return crud.get_historial_by_cuenta(db, cuenta_id, limit)


@router.get("/estadisticas/cuenta/{cuenta_id}", response_model=EstadisticasExtraccion)
def obtener_estadisticas_cuenta(
    cuenta_id: int,
    dias: int = Query(30, ge=1, le=365, description="Días hacia atrás para estadísticas"),
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """Obtiene estadísticas de extracción de una cuenta."""
    cuenta = crud.get_cuenta_correo(db, cuenta_id)
    if not cuenta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuenta de correo con ID {cuenta_id} no encontrada"
        )

    stats = crud.get_estadisticas_extraccion(db, cuenta_id, dias)
    ultima = crud.get_ultima_extraccion(db, cuenta_id)

    return EstadisticasExtraccion(
        cuenta_correo_id=cuenta_id,
        email=cuenta.email,
        total_ejecuciones=stats["total_ejecuciones"],
        ultima_ejecucion=ultima.fecha_ejecucion if ultima else None,
        total_facturas_encontradas=stats["total_facturas_encontradas"],
        total_facturas_creadas=stats["total_facturas_creadas"],
        tasa_exito=stats["tasa_exito"],
        promedio_tiempo_ms=stats["promedio_tiempo_ms"],
    )


# ==================== Endpoints para Invoice Extractor ====================

@router.get("/configuracion-extractor-public", response_model=ConfiguracionExtractorResponse)
def obtener_configuracion_para_extractor_public(
    db: Session = Depends(get_db),
):
    """
    **Endpoint PÚBLICO para invoice_extractor** (sin autenticación).

    Obtiene configuración en formato JSON para el invoice_extractor.

    Solo incluye cuentas activas con NITs activos.
    """
    cuentas_activas = crud.get_cuentas_activas_para_extraccion(db)

    users = []
    total_nits = 0

    for cuenta in cuentas_activas:
        # Filtrar solo NITs activos
        nits_activos = [nit.nit for nit in cuenta.nits if nit.activo]

        if nits_activos:  # Solo incluir cuentas con al menos un NIT activo
            users.append(
                ConfiguracionExtractorEmail(
                    cuenta_id=cuenta.id,
                    email=cuenta.email,
                    nits=nits_activos,
                    max_correos_por_ejecucion=cuenta.max_correos_por_ejecucion,
                    ventana_inicial_dias=cuenta.ventana_inicial_dias,
                    ultima_ejecucion_exitosa=cuenta.ultima_ejecucion_exitosa,
                    fecha_ultimo_correo_procesado=cuenta.fecha_ultimo_correo_procesado,
                )
            )
            total_nits += len(nits_activos)

    return ConfiguracionExtractorResponse(
        users=users,
        total_cuentas=len(users),
        total_nits=total_nits,
        generado_en=datetime.utcnow(),
    )


@router.get("/configuracion-extractor", response_model=ConfiguracionExtractorResponse)
def obtener_configuracion_para_extractor(
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    """
    Obtiene configuración en formato JSON para el invoice_extractor.

    **Formato compatible con extracción incremental:**
    ```json
    {
      "users": [
        {
          "email": "facturacion@empresa.com",
          "nits": ["123456", "789012"],
          "max_correos_por_ejecucion": 10000,
          "ventana_inicial_dias": 30,
          "ultima_ejecucion_exitosa": "2025-01-15T10:30:00Z",
          "fecha_ultimo_correo_procesado": "2025-01-15T09:45:00Z"
        }
      ]
    }
    ```

    Solo incluye cuentas activas con NITs activos.
    """
    cuentas_activas = crud.get_cuentas_activas_para_extraccion(db)

    users = []
    total_nits = 0

    for cuenta in cuentas_activas:
        # Filtrar solo NITs activos
        nits_activos = [nit.nit for nit in cuenta.nits if nit.activo]

        if nits_activos:  # Solo incluir cuentas con al menos un NIT activo
            users.append(
                ConfiguracionExtractorEmail(
                    cuenta_id=cuenta.id,
                    email=cuenta.email,
                    nits=nits_activos,
                    max_correos_por_ejecucion=cuenta.max_correos_por_ejecucion,
                    ventana_inicial_dias=cuenta.ventana_inicial_dias,
                    ultima_ejecucion_exitosa=cuenta.ultima_ejecucion_exitosa,
                    fecha_ultimo_correo_procesado=cuenta.fecha_ultimo_correo_procesado,
                )
            )
            total_nits += len(nits_activos)

    return ConfiguracionExtractorResponse(
        users=users,
        total_cuentas=len(users),
        total_nits=total_nits,
        generado_en=datetime.utcnow(),
    )
