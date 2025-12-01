# app/api/v1/routers/dashboard.py
"""
Dashboard optimizado con Progressive Disclosure (Option A)

Endpoints para vista principal del dashboard con filtrado dinámico:
- Mes actual + estados activos (dashboard principal)
- Alerta de fin de mes (contextual)
- Histórico completo (vista separada)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, and_, or_
from typing import List, Optional
from datetime import datetime, date
from calendar import monthrange

from app.db.session import get_db
from app.core.security import get_current_usuario, require_role
from app.models.factura import Factura, EstadoFactura
from app.models.proveedor import Proveedor
from app.models.workflow_aprobacion import WorkflowAprobacionFactura
from app.schemas.factura import FacturaRead
from pydantic import BaseModel, Field
from app.utils.logger import logger


router = APIRouter(tags=["Dashboard"])


# ============================================================================
# SCHEMAS
# ============================================================================

class EstadisticasMesActual(BaseModel):
    """Estadísticas del mes actual (solo estados activos)"""
    total: int = Field(description="Total de facturas del mes actual")
    en_revision: int = Field(description="Facturas en revisión (requieren acción responsable)")
    aprobadas: int = Field(description="Facturas aprobadas (requieren acción contador)")
    aprobadas_auto: int = Field(description="Facturas aprobadas automáticamente (requieren acción contador)")
    rechazadas: int = Field(description="Facturas rechazadas (inactivas)")


class DashboardMesActualResponse(BaseModel):
    """Respuesta completa del dashboard del mes actual"""
    mes: int = Field(description="Mes actual (1-12)")
    año: int = Field(description="Año actual")
    nombre_mes: str = Field(description="Nombre del mes en español")
    estadisticas: EstadisticasMesActual
    facturas: List[FacturaRead]
    total_facturas: int = Field(description="Total de facturas retornadas")


class AlertaMesResponse(BaseModel):
    """Respuesta de alerta de fin de mes"""
    mostrar_alerta: bool = Field(description="Si se debe mostrar la alerta")
    dias_restantes: int = Field(description="Días restantes para fin de mes")
    facturas_pendientes: int = Field(description="Facturas pendientes (en_revision + aprobadas)")
    mensaje: Optional[str] = Field(None, description="Mensaje de alerta personalizado")
    nivel_urgencia: str = Field(description="Nivel de urgencia: info, warning, critical")


class EstadisticasHistorico(BaseModel):
    """Estadísticas del período histórico (todos los estados)"""
    total: int = Field(description="Total de facturas del período")
    validadas: int = Field(description="Facturas validadas por contador")
    devueltas: int = Field(description="Facturas devueltas por contador")
    rechazadas: int = Field(description="Facturas rechazadas por responsable")
    pendientes: int = Field(description="Facturas aún pendientes (en_revision + aprobadas)")


class HistoricoResponse(BaseModel):
    """Respuesta completa de vista histórica"""
    mes: int = Field(description="Mes consultado")
    año: int = Field(description="Año consultado")
    nombre_mes: str = Field(description="Nombre del mes en español")
    estadisticas: EstadisticasHistorico
    facturas: List[FacturaRead]
    total_facturas: int = Field(description="Total de facturas retornadas")


# ============================================================================
# UTILIDADES
# ============================================================================

MESES_ESPAÑOL = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def get_mes_actual():
    """Retorna mes y año actual"""
    hoy = date.today()
    return hoy.month, hoy.year


def get_dias_restantes_mes() -> int:
    """Calcula días restantes hasta fin de mes"""
    hoy = date.today()
    ultimo_dia = monthrange(hoy.year, hoy.month)[1]
    ultimo_dia_mes = date(hoy.year, hoy.month, ultimo_dia)
    return (ultimo_dia_mes - hoy).days


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get(
    "/mes-actual",
    response_model=DashboardMesActualResponse,
    summary="Dashboard del mes actual (Progressive Disclosure)",
    description="""
    Retorna facturas del mes actual en estados ACTIVOS únicamente.

    Estados activos:
    - en_revision (requiere acción responsable)
    - aprobada (requiere acción contador)
    - aprobada_auto (requiere acción contador)
    - rechazada (para referencia)

    NO incluye:
    - validada_contabilidad (ya procesada)
    - devuelta_contabilidad (ya procesada)

    Optimizado con índices en (año, mes, estado).
    """
)
def get_dashboard_mes_actual(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_usuario)
):
    """
    Dashboard principal: solo mes actual + estados activos.

    Implementa Progressive Disclosure (Option A):
    - Focus en facturas que requieren ACCIÓN
    - Sin saturación de información
    - Performance optimizada
    """
    try:
        mes_actual, año_actual = get_mes_actual()

        logger.info(f"Dashboard mes actual solicitado: {MESES_ESPAÑOL[mes_actual]} {año_actual} por usuario {current_user.usuario}")

        # Estados activos (facturas que requieren atención o son del mes)
        estados_activos = [
            EstadoFactura.en_revision.value,
            EstadoFactura.aprobada.value,
            EstadoFactura.aprobada_auto.value,
            EstadoFactura.rechazada.value
        ]

        # Query principal: mes actual + estados activos
        query = db.query(Factura).options(
            joinedload(Factura.proveedor),
            joinedload(Factura.usuario)
        ).filter(
            extract('month', Factura.creado_en) == mes_actual,
            extract('year', Factura.creado_en) == año_actual,
            Factura.estado.in_(estados_activos)
        ).order_by(
            # Priorizar por estado (las que requieren acción primero)
            Factura.estado,
            Factura.creado_en.desc()
        )

        facturas = query.all()

        # Calcular estadísticas
        total = len(facturas)
        en_revision = sum(1 for f in facturas if f.estado == EstadoFactura.en_revision.value)
        aprobadas = sum(1 for f in facturas if f.estado == EstadoFactura.aprobada.value)
        aprobadas_auto = sum(1 for f in facturas if f.estado == EstadoFactura.aprobada_auto.value)
        rechazadas = sum(1 for f in facturas if f.estado == EstadoFactura.rechazada.value)

        logger.info(
            f"Dashboard mes actual: {total} facturas "
            f"(en_revision: {en_revision}, aprobadas: {aprobadas}, "
            f"aprobadas_auto: {aprobadas_auto}, rechazadas: {rechazadas})"
        )

        return DashboardMesActualResponse(
            mes=mes_actual,
            año=año_actual,
            nombre_mes=MESES_ESPAÑOL[mes_actual],
            estadisticas=EstadisticasMesActual(
                total=total,
                en_revision=en_revision,
                aprobadas=aprobadas,
                aprobadas_auto=aprobadas_auto,
                rechazadas=rechazadas
            ),
            facturas=[FacturaRead.model_validate(f) for f in facturas],
            total_facturas=total
        )

    except Exception as e:
        logger.error(f"Error en dashboard mes actual: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener dashboard del mes actual: {str(e)}"
        )


@router.get(
    "/alerta-mes",
    response_model=AlertaMesResponse,
    summary="Alerta contextual de fin de mes",
    description="""
    Retorna si se debe mostrar alerta de fin de mes.

    Lógica de alerta:
    - Solo se muestra si días_restantes < 5 Y hay facturas pendientes
    - Facturas pendientes = en_revision + aprobada + aprobada_auto

    Niveles de urgencia:
    - info: 4-5 días restantes
    - warning: 2-3 días restantes
    - critical: 0-1 días restantes
    """
)
def get_alerta_mes(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_usuario)
):
    """
    Alerta contextual: solo muestra si hay facturas pendientes cerca de fin de mes.

    UX Senior:
    - No invasiva (banner superior)
    - Solo aparece cuando es relevante
    - Mensaje personalizado según urgencia
    """
    try:
        mes_actual, año_actual = get_mes_actual()
        dias_restantes = get_dias_restantes_mes()

        # Contar facturas pendientes del mes actual
        estados_pendientes = [
            EstadoFactura.en_revision.value,
            EstadoFactura.aprobada.value,
            EstadoFactura.aprobada_auto.value
        ]

        facturas_pendientes = db.query(func.count(Factura.id)).filter(
            extract('month', Factura.creado_en) == mes_actual,
            extract('year', Factura.creado_en) == año_actual,
            Factura.estado.in_(estados_pendientes)
        ).scalar()

        # Decidir si mostrar alerta
        mostrar_alerta = (dias_restantes < 5) and (facturas_pendientes > 0)

        # Determinar nivel de urgencia
        if dias_restantes <= 1:
            nivel_urgencia = "critical"
            if dias_restantes == 0:
                mensaje = f"🚨 Tienes {facturas_pendientes} factura(s) pendiente(s). El mes cierra HOY."
            else:
                mensaje = f"🚨 Tienes {facturas_pendientes} factura(s) pendiente(s). El mes cierra MAÑANA."
        elif dias_restantes <= 3:
            nivel_urgencia = "warning"
            mensaje = f"⚠️ Tienes {facturas_pendientes} factura(s) pendiente(s). El mes cierra en {dias_restantes} días."
        else:
            nivel_urgencia = "info"
            mensaje = f"⚠️ Tienes {facturas_pendientes} factura(s) pendiente(s). El mes cierra en {dias_restantes} días."

        logger.info(
            f"Alerta mes: mostrar={mostrar_alerta}, días={dias_restantes}, "
            f"pendientes={facturas_pendientes}, urgencia={nivel_urgencia}"
        )

        return AlertaMesResponse(
            mostrar_alerta=mostrar_alerta,
            dias_restantes=dias_restantes,
            facturas_pendientes=facturas_pendientes,
            mensaje=mensaje if mostrar_alerta else None,
            nivel_urgencia=nivel_urgencia
        )

    except Exception as e:
        logger.error(f"Error en alerta mes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al calcular alerta de mes: {str(e)}"
        )


@router.get(
    "/historico",
    response_model=HistoricoResponse,
    summary="Vista histórica completa (análisis)",
    description="""
    Retorna TODAS las facturas de un período específico (todos los estados).

    Incluye todos los estados:
    - en_revision, aprobada, aprobada_auto (aún pendientes)
    - validada_contabilidad (completadas exitosamente)
    - devuelta_contabilidad (devueltas por contador)
    - rechazada (rechazadas por responsable)

    Usar para:
    - Análisis histórico
    - Reportes mensuales
    - Auditoría
    - Exportaciones
    """
)
def get_historico(
    mes: int = Query(..., ge=1, le=12, description="Mes a consultar (1-12)"),
    anio: int = Query(..., ge=2020, le=2100, description="Año a consultar"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_usuario)
):
    """
    Vista histórica: análisis completo de un período.

    Progressive Disclosure:
    - Dashboard principal = Acción (mes actual, estados activos)
    - Histórico = Análisis (cualquier mes, todos los estados)
    """
    try:
        logger.info(f"Histórico solicitado: {MESES_ESPAÑOL[mes]} {anio} por usuario {current_user.usuario}")

        # Query: mes específico + TODOS los estados
        query = db.query(Factura).options(
            joinedload(Factura.proveedor),
            joinedload(Factura.usuario)
        ).filter(
            extract('month', Factura.creado_en) == mes,
            extract('year', Factura.creado_en) == anio
        ).order_by(
            Factura.creado_en.desc()
        )

        facturas = query.all()

        # Calcular estadísticas completas
        total = len(facturas)
        validadas = sum(1 for f in facturas if f.estado == EstadoFactura.validada_contabilidad.value)
        devueltas = sum(1 for f in facturas if f.estado == EstadoFactura.devuelta_contabilidad.value)
        rechazadas = sum(1 for f in facturas if f.estado == EstadoFactura.rechazada.value)

        # Pendientes = estados que aún requieren acción
        estados_pendientes = [
            EstadoFactura.en_revision.value,
            EstadoFactura.aprobada.value,
            EstadoFactura.aprobada_auto.value
        ]
        pendientes = sum(1 for f in facturas if f.estado in estados_pendientes)

        logger.info(
            f"Histórico {MESES_ESPAÑOL[mes]} {anio}: {total} facturas "
            f"(validadas: {validadas}, devueltas: {devueltas}, "
            f"rechazadas: {rechazadas}, pendientes: {pendientes})"
        )

        return HistoricoResponse(
            mes=mes,
            año=anio,
            nombre_mes=MESES_ESPAÑOL[mes],
            estadisticas=EstadisticasHistorico(
                total=total,
                validadas=validadas,
                devueltas=devueltas,
                rechazadas=rechazadas,
                pendientes=pendientes
            ),
            facturas=[FacturaRead.model_validate(f) for f in facturas],
            total_facturas=total
        )

    except Exception as e:
        logger.error(f"Error en histórico: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener histórico: {str(e)}"
        )
