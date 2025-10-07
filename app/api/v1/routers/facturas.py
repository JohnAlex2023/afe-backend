# app/api/v1/routers/facturas.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.schemas.factura import FacturaCreate, FacturaRead
from app.schemas.common import ErrorResponse
from app.services.invoice_service import process_and_persist_invoice
from app.core.security import get_current_responsable, require_role
from app.crud.factura import (
    list_facturas,
    get_factura,
    find_by_cufe,
    get_factura_by_numero,
    get_facturas_resumen_por_mes,
    get_facturas_por_periodo,
    count_facturas_por_periodo,
    get_estadisticas_periodo,
    get_años_disponibles,
    get_jerarquia_facturas,
)
from app.utils.logger import logger


router = APIRouter(tags=["Facturas"])


# -----------------------------------------------------
# Listar todas las facturas (con filtros opcionales)
# -----------------------------------------------------
@router.get(
    "/",
    response_model=List[FacturaRead],
    summary="Listar facturas",
    description="Obtiene facturas. Admin puede ver todas o solo asignadas, Responsable solo sus proveedores."
)
def list_all(
    skip: int = 0,
    limit: int = 100,
    nit: Optional[str] = None,
    numero_factura: Optional[str] = None,
    solo_asignadas: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Lista facturas con control de acceso basado en roles:
    - Admin: Ve TODAS las facturas (o solo asignadas si solo_asignadas=true)
    - Responsable: Solo ve facturas de proveedores (NITs) que tiene asignados
    """
    # Determinar si se debe filtrar por responsable
    responsable_id = None
    if hasattr(current_user, 'role') and current_user.role.nombre == 'responsable':
        # Si es responsable, SIEMPRE filtrar solo sus proveedores asignados
        responsable_id = current_user.id
        logger.info(
            f"Responsable {current_user.usuario} (ID: {current_user.id}) accediendo a sus facturas asignadas"
        )
    elif solo_asignadas:
        # Si es admin y solicita solo asignadas, filtrar por sus proveedores
        responsable_id = current_user.id
        logger.info(f"Admin {current_user.usuario} viendo solo facturas asignadas")
    else:
        logger.info(f"Admin {current_user.usuario} viendo todas las facturas")

    return list_facturas(
        db,
        skip=skip,
        limit=limit,
        nit=nit,
        numero_factura=numero_factura,
        responsable_id=responsable_id
    )


# -----------------------------------------------------
# Crear o actualizar factura
# -----------------------------------------------------
@router.post(
    "/",
    response_model=FacturaRead,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
    summary="Crear o actualizar factura",
    description="Procesa una nueva factura. Si ya existe, devuelve un error de conflicto."
)
def create_invoice(
    payload: FacturaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable")),
):
    result, action = process_and_persist_invoice(
        db, payload, created_by=current_user.usuario
    )

    if action == "conflict":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflicto con factura existente"
        )

    f = get_factura(db, result["id"])
    logger.info(
        "Factura procesada",
        extra={"id": f.id, "usuario": current_user.usuario, "action": action}
    )
    return f


# -----------------------------------------------------
# Obtener factura por ID
# -----------------------------------------------------
@router.get(
    "/{factura_id}",
    response_model=FacturaRead,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener factura por ID",
    description="Devuelve los datos de una factura específica por ID."
)
def get_one(
    factura_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    f = get_factura(db, factura_id)
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )
    return f


# -----------------------------------------------------
# Obtener facturas por NIT
# -----------------------------------------------------
@router.get(
    "/nit/{nit}",
    response_model=List[FacturaRead],
    summary="Listar facturas por NIT",
    description="Obtiene todas las facturas asociadas a un proveedor por NIT."
)
def get_by_nit(
    nit: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    return list_facturas(db, skip=skip, limit=limit, nit=nit)


# -----------------------------------------------------
# Obtener factura por CUFE
# -----------------------------------------------------
@router.get(
    "/cufe/{cufe}",
    response_model=FacturaRead,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener factura por CUFE",
    description="Devuelve una factura única usando el CUFE."
)
def get_by_cufe(
    cufe: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    f = find_by_cufe(db, cufe)
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )
    return f


# -----------------------------------------------------
# Obtener factura por número de factura
# -----------------------------------------------------
@router.get(
    "/numero/{numero_factura}",
    response_model=FacturaRead,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener factura por número de factura",
    description="Devuelve una factura única usando el número de factura."
)
def get_by_numero(
    numero_factura: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    f = get_factura_by_numero(db, numero_factura)
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )
    return f


# -----------------------------------------------------
# Aprobar factura
# -----------------------------------------------------
@router.post(
    "/{factura_id}/aprobar",
    response_model=FacturaRead,
    summary="Aprobar factura",
    description="Aprueba una factura cambiando su estado a 'aprobado'"
)
def aprobar_factura(
    factura_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Aprueba una factura y registra quién la aprobó.

    Parámetros esperados en payload:
    - aprobado_por: Usuario que aprueba
    - observaciones (opcional): Comentarios adicionales
    """
    from app.models.factura import Factura
    from app.models.estado_factura import EstadoFactura
    from datetime import datetime

    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )

    # Actualizar estado
    factura.estado = EstadoFactura.aprobada
    factura.aprobado_por = payload.get("aprobado_por", current_user.usuario)
    factura.fecha_aprobacion = datetime.now()
    if payload.get("observaciones"):
        factura.observaciones = payload.get("observaciones")

    db.commit()
    db.refresh(factura)

    logger.info(
        f"Factura {factura.numero_factura} aprobada por {current_user.usuario}",
        extra={"factura_id": factura_id, "usuario": current_user.usuario}
    )

    return factura


# -----------------------------------------------------
# Rechazar factura
# -----------------------------------------------------
@router.post(
    "/{factura_id}/rechazar",
    response_model=FacturaRead,
    summary="Rechazar factura",
    description="Rechaza una factura cambiando su estado a 'rechazado'"
)
def rechazar_factura(
    factura_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Rechaza una factura y registra el motivo.

    Parámetros esperados en payload:
    - rechazado_por: Usuario que rechaza
    - motivo: Razón del rechazo (requerido)
    """
    from app.models.factura import Factura
    from app.models.estado_factura import EstadoFactura
    from datetime import datetime

    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )

    if not payload.get("motivo"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El motivo de rechazo es requerido"
        )

    # Actualizar estado
    factura.estado = EstadoFactura.rechazada
    factura.rechazado_por = payload.get("rechazado_por", current_user.usuario)
    factura.fecha_rechazo = datetime.now()
    factura.motivo_rechazo = payload.get("motivo")

    db.commit()
    db.refresh(factura)

    logger.info(
        f"Factura {factura.numero_factura} rechazada por {current_user.usuario}. Motivo: {payload.get('motivo')}",
        extra={"factura_id": factura_id, "usuario": current_user.usuario}
    )

    return factura


# ✨ ENDPOINTS PARA CLASIFICACIÓN POR PERÍODOS MENSUALES ✨

# -----------------------------------------------------
# Obtener resumen de facturas agrupadas por mes
# -----------------------------------------------------
@router.get(
    "/periodos/resumen",
    tags=["Reportes - Períodos Mensuales"],
    summary="Resumen de facturas por mes",
    description="Obtiene un resumen de facturas agrupadas por mes/año con totales agregados. Ideal para dashboards y reportes mensuales."
)
def get_resumen_por_mes(
    año: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Retorna facturas agrupadas por período (mes/año) con:
    - Total de facturas por mes
    - Monto total por mes
    - Subtotal e IVA por mes

    Ejemplo de respuesta:
    [
        {
            "periodo": "2025-07",
            "año": 2025,
            "mes": 7,
            "total_facturas": 6,
            "monto_total": 17126907.00,
            "subtotal_total": 14000000.00,
            "iva_total": 3126907.00
        },
        ...
    ]
    """
    return get_facturas_resumen_por_mes(
        db=db,
        año=año,
        proveedor_id=proveedor_id,
        estado=estado
    )


# -----------------------------------------------------
# Obtener facturas de un período específico
# -----------------------------------------------------
@router.get(
    "/periodos/{periodo}",
    response_model=List[FacturaRead],
    tags=["Reportes - Períodos Mensuales"],
    summary="Facturas de un período específico",
    description="Obtiene todas las facturas de un mes/año específico (formato: YYYY-MM)"
)
def get_facturas_periodo(
    periodo: str,
    skip: int = 0,
    limit: int = 100,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Obtiene facturas de un período específico.

    Args:
        periodo: Formato "YYYY-MM" (ej: "2025-07" para julio 2025)
        skip: Registros a saltar (paginación)
        limit: Máximo de registros a retornar
        proveedor_id: Filtrar por proveedor (opcional)
        estado: Filtrar por estado (opcional)

    Returns:
        Lista de facturas del período
    """
    # Validar formato de período
    if len(periodo) != 7 or periodo[4] != '-':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de período inválido. Use YYYY-MM (ej: 2025-07)"
        )

    facturas = get_facturas_por_periodo(
        db=db,
        periodo=periodo,
        skip=skip,
        limit=limit,
        proveedor_id=proveedor_id,
        estado=estado
    )

    return facturas


# -----------------------------------------------------
# Obtener estadísticas de un período
# -----------------------------------------------------
@router.get(
    "/periodos/{periodo}/estadisticas",
    tags=["Reportes - Períodos Mensuales"],
    summary="Estadísticas de un período",
    description="Obtiene estadísticas detalladas de un período específico incluyendo desglose por estado"
)
def get_stats_periodo(
    periodo: str,
    proveedor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Retorna estadísticas completas de un período:
    - Total de facturas
    - Monto total, subtotal, IVA
    - Promedio por factura
    - Desglose por estado (pendiente, aprobada, etc.)

    Ejemplo de respuesta:
    {
        "periodo": "2025-07",
        "total_facturas": 6,
        "monto_total": 17126907.00,
        "subtotal": 14000000.00,
        "iva": 3126907.00,
        "promedio": 2854484.50,
        "por_estado": [
            {"estado": "en_revision", "cantidad": 6, "monto": 17126907.00}
        ]
    }
    """
    # Validar formato
    if len(periodo) != 7 or periodo[4] != '-':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de período inválido. Use YYYY-MM"
        )

    return get_estadisticas_periodo(
        db=db,
        periodo=periodo,
        proveedor_id=proveedor_id
    )


# -----------------------------------------------------
# Contar facturas de un período
# -----------------------------------------------------
@router.get(
    "/periodos/{periodo}/count",
    tags=["Reportes - Períodos Mensuales"],
    summary="Contar facturas de un período",
    description="Retorna el número total de facturas en un período"
)
def count_periodo(
    periodo: str,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Cuenta facturas de un período específico.
    Útil para paginación y reportes rápidos.
    """
    if len(periodo) != 7 or periodo[4] != '-':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de período inválido. Use YYYY-MM"
        )

    count = count_facturas_por_periodo(
        db=db,
        periodo=periodo,
        proveedor_id=proveedor_id,
        estado=estado
    )

    return {"periodo": periodo, "total": count}


# -----------------------------------------------------
# Obtener años disponibles
# -----------------------------------------------------
@router.get(
    "/periodos/años/disponibles",
    tags=["Reportes - Períodos Mensuales"],
    summary="Años con facturas",
    description="Retorna lista de años que tienen facturas registradas"
)
def get_años(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Retorna años disponibles en orden descendente.
    Útil para filtros en frontend.

    Ejemplo: [2025, 2024, 2023]
    """
    años = get_años_disponibles(db)
    return {"años": años}


# -----------------------------------------------------
# Jerarquía empresarial: Año → Mes → Facturas
# -----------------------------------------------------
@router.get(
    "/periodos/jerarquia",
    tags=["Reportes - Períodos Mensuales"],
    summary="Vista jerárquica año→mes→facturas",
    description="Retorna facturas organizadas jerárquicamente por año y mes. Ideal para dashboards con drill-down."
)
def get_jerarquia(
    año: Optional[int] = None,
    mes: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None,
    limit_por_mes: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    **Vista Jerárquica Empresarial** para organización cronológica de facturas.

    Retorna estructura anidada:
    ```json
    {
        "2025": {
            "10": {
                "total_facturas": 4,
                "monto_total": 12500.00,
                "subtotal": 10500.00,
                "iva": 2000.00,
                "facturas": [
                    {
                        "id": 123,
                        "numero_factura": "FACT-001",
                        "fecha_emision": "2025-10-15",
                        "total": 5000.00,
                        "estado": "aprobada"
                    },
                    ...
                ]
            },
            "09": {...}
        },
        "2024": {...}
    }
    ```

    **Filtros disponibles:**
    - `año`: Filtrar por año específico (ej: 2025)
    - `mes`: Filtrar por mes específico (1-12)
    - `proveedor_id`: Filtrar por proveedor
    - `estado`: Filtrar por estado
    - `limit_por_mes`: Límite de facturas por mes (default: 100)

    **Orden:** Año DESC → Mes DESC → Fecha DESC (más recientes primero)

    **Performance:** Usa índice `idx_facturas_orden_cronologico` para queries ultra-rápidas
    """
    return get_jerarquia_facturas(
        db=db,
        año=año,
        mes=mes,
        proveedor_id=proveedor_id,
        estado=estado,
        limit_por_mes=limit_por_mes
    )
