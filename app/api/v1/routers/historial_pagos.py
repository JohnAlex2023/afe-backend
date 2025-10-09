"""
API REST para gestión de historial de pagos y patrones de automatización.

Endpoints enterprise:
- POST /analizar-patrones: Ejecuta análisis de patrones desde BD
- GET /patrones: Lista todos los patrones históricos
- GET /patrones/{proveedor_id}: Patrones de un proveedor específico
- GET /estadisticas: Estadísticas globales de patrones
- GET /patrones/{id}: Detalle de un patrón específico

Nivel: Enterprise Fortune 500
Autor: Sistema de Automatización AFE
Fecha: 2025-10-08
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.models.historial_pagos import HistorialPagos, TipoPatron
from app.services.analisis_patrones_service import AnalizadorPatronesService


router = APIRouter(prefix="/historial-pagos", tags=["Historial de Pagos"])


# ============================================================================
# SCHEMAS PYDANTIC
# ============================================================================

class AnalizarPatronesRequest(BaseModel):
    """Request para análisis de patrones."""
    ventana_meses: int = Field(default=12, ge=1, le=24, description="Meses hacia atrás a analizar")
    solo_proveedores: Optional[List[int]] = Field(default=None, description="IDs de proveedores a analizar")
    forzar_recalculo: bool = Field(default=False, description="Forzar recálculo de patrones existentes")


class PatronHistoricoResponse(BaseModel):
    """Response de patrón histórico."""
    id: int
    proveedor_id: int
    proveedor_nombre: Optional[str] = None
    concepto_normalizado: str
    tipo_patron: str
    pagos_analizados: int
    meses_con_pagos: int
    monto_promedio: float
    monto_minimo: float
    monto_maximo: float
    desviacion_estandar: float
    coeficiente_variacion: float
    frecuencia_detectada: Optional[str] = None
    puede_aprobar_auto: bool
    umbral_alerta: Optional[float] = None
    fecha_analisis: Optional[str] = None

    class Config:
        from_attributes = True


class EstadisticasPatronesResponse(BaseModel):
    """Response de estadísticas globales."""
    total: int
    por_tipo: dict
    auto_aprobables: int
    porcentaje_automatizable: float
    proveedores_unicos: int


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/analizar-patrones",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Ejecutar análisis de patrones desde BD",
    description="""
    Ejecuta análisis de patrones históricos desde facturas de la BD.

    Este endpoint:
    - Analiza facturas de los últimos N meses
    - Calcula estadísticas por proveedor + concepto
    - Clasifica patrones en TIPO_A/B/C
    - Actualiza/crea registros en historial_pagos

    **Uso recomendado:** Ejecutar diariamente o semanalmente vía tarea programada.
    """
)
def analizar_patrones_desde_bd(
    request: AnalizarPatronesRequest,
    db: Session = Depends(get_db)
):
    """
    Ejecuta análisis de patrones desde la base de datos.
    """
    try:
        analizador = AnalizadorPatronesService(db)

        resultado = analizador.analizar_patrones_desde_bd(
            ventana_meses=request.ventana_meses,
            solo_proveedores=request.solo_proveedores,
            forzar_recalculo=request.forzar_recalculo
        )

        if not resultado['exito']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=resultado.get('mensaje', 'Error desconocido en análisis')
            )

        return {
            "success": True,
            "message": "Análisis completado exitosamente",
            "data": resultado
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ejecutando análisis de patrones: {str(e)}"
        )


@router.get(
    "/patrones",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Listar todos los patrones históricos",
    description="Obtiene listado de patrones históricos con filtros opcionales."
)
def listar_patrones(
    proveedor_id: Optional[int] = Query(None, description="Filtrar por proveedor"),
    tipo_patron: Optional[str] = Query(None, description="Filtrar por tipo (TIPO_A, TIPO_B, TIPO_C)"),
    solo_auto_aprobables: bool = Query(False, description="Solo patrones auto-aprobables"),
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(50, ge=1, le=500, description="Cantidad de registros"),
    db: Session = Depends(get_db)
):
    """
    Lista patrones históricos con filtros.
    """
    try:
        query = db.query(HistorialPagos)

        # Aplicar filtros
        if proveedor_id:
            query = query.filter(HistorialPagos.proveedor_id == proveedor_id)

        if tipo_patron:
            try:
                tipo_enum = TipoPatron[tipo_patron]
                query = query.filter(HistorialPagos.tipo_patron == tipo_enum)
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tipo de patrón inválido. Opciones: TIPO_A, TIPO_B, TIPO_C"
                )

        if solo_auto_aprobables:
            query = query.filter(HistorialPagos.puede_aprobar_auto == 1)

        # Contar total antes de paginación
        total = query.count()

        # Aplicar paginación
        patrones = query.order_by(
            HistorialPagos.fecha_analisis.desc()
        ).offset(skip).limit(limit).all()

        # Serializar resultados
        resultados = []
        for patron in patrones:
            resultados.append({
                "id": patron.id,
                "proveedor_id": patron.proveedor_id,
                "proveedor_nombre": patron.proveedor.razon_social if patron.proveedor else None,
                "concepto_normalizado": patron.concepto_normalizado,
                "tipo_patron": patron.tipo_patron.value,
                "pagos_analizados": patron.pagos_analizados,
                "meses_con_pagos": patron.meses_con_pagos,
                "monto_promedio": float(patron.monto_promedio),
                "monto_minimo": float(patron.monto_minimo),
                "monto_maximo": float(patron.monto_maximo),
                "desviacion_estandar": float(patron.desviacion_estandar),
                "coeficiente_variacion": float(patron.coeficiente_variacion),
                "frecuencia_detectada": patron.frecuencia_detectada,
                "puede_aprobar_auto": patron.puede_aprobar_auto == 1,
                "umbral_alerta": float(patron.umbral_alerta) if patron.umbral_alerta else None,
                "fecha_analisis": patron.fecha_analisis.isoformat() if patron.fecha_analisis else None
            })

        return {
            "success": True,
            "data": {
                "patrones": resultados,
                "total": total,
                "skip": skip,
                "limit": limit
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listando patrones: {str(e)}"
        )


@router.get(
    "/estadisticas",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Obtener estadísticas globales de patrones",
    description="Retorna métricas agregadas de todos los patrones históricos."
)
def obtener_estadisticas(
    proveedor_id: Optional[int] = Query(None, description="Filtrar por proveedor"),
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas globales de patrones.
    """
    try:
        analizador = AnalizadorPatronesService(db)
        stats = analizador.obtener_estadisticas_patrones(proveedor_id=proveedor_id)

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@router.get(
    "/patrones/{patron_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Obtener detalle de un patrón específico",
    description="Retorna información detallada de un patrón histórico por ID."
)
def obtener_patron_detalle(
    patron_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene detalle completo de un patrón histórico.
    """
    try:
        patron = db.query(HistorialPagos).filter(
            HistorialPagos.id == patron_id
        ).first()

        if not patron:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patrón con ID {patron_id} no encontrado"
            )

        # Serializar con todos los detalles
        detalle = {
            "id": patron.id,
            "proveedor_id": patron.proveedor_id,
            "proveedor": {
                "id": patron.proveedor.id,
                "razon_social": patron.proveedor.razon_social,
                "nit": patron.proveedor.nit
            } if patron.proveedor else None,
            "concepto_normalizado": patron.concepto_normalizado,
            "concepto_hash": patron.concepto_hash,
            "tipo_patron": patron.tipo_patron.value,
            "clasificacion": {
                "tipo": patron.tipo_patron.value,
                "descripcion": "Valor fijo" if patron.tipo_patron == TipoPatron.TIPO_A else
                              "Fluctuante predecible" if patron.tipo_patron == TipoPatron.TIPO_B else
                              "Excepcional"
            },
            "estadisticas": {
                "pagos_analizados": patron.pagos_analizados,
                "meses_con_pagos": patron.meses_con_pagos,
                "monto_promedio": float(patron.monto_promedio),
                "monto_minimo": float(patron.monto_minimo),
                "monto_maximo": float(patron.monto_maximo),
                "desviacion_estandar": float(patron.desviacion_estandar),
                "coeficiente_variacion": float(patron.coeficiente_variacion),
                "rango_inferior": float(patron.rango_inferior) if patron.rango_inferior else None,
                "rango_superior": float(patron.rango_superior) if patron.rango_superior else None
            },
            "recurrencia": {
                "frecuencia_detectada": patron.frecuencia_detectada,
                "ultimo_pago_fecha": patron.ultimo_pago_fecha.isoformat() if patron.ultimo_pago_fecha else None,
                "ultimo_pago_monto": float(patron.ultimo_pago_monto) if patron.ultimo_pago_monto else None
            },
            "automatizacion": {
                "puede_aprobar_auto": patron.puede_aprobar_auto == 1,
                "umbral_alerta": float(patron.umbral_alerta) if patron.umbral_alerta else None
            },
            "metadata": {
                "fecha_analisis": patron.fecha_analisis.isoformat() if patron.fecha_analisis else None,
                "version_algoritmo": patron.version_algoritmo,
                "creado_en": patron.creado_en.isoformat() if patron.creado_en else None,
                "actualizado_en": patron.actualizado_en.isoformat() if patron.actualizado_en else None
            }
        }

        return {
            "success": True,
            "data": detalle
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo detalle del patrón: {str(e)}"
        )


@router.get(
    "/proveedor/{proveedor_id}/patrones",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Obtener todos los patrones de un proveedor",
    description="Lista todos los patrones históricos asociados a un proveedor."
)
def obtener_patrones_proveedor(
    proveedor_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los patrones de un proveedor específico.
    """
    try:
        patrones = db.query(HistorialPagos).filter(
            HistorialPagos.proveedor_id == proveedor_id
        ).order_by(
            HistorialPagos.puede_aprobar_auto.desc(),
            HistorialPagos.monto_promedio.desc()
        ).all()

        if not patrones:
            return {
                "success": True,
                "data": {
                    "proveedor_id": proveedor_id,
                    "patrones": [],
                    "total": 0,
                    "mensaje": "No se encontraron patrones para este proveedor"
                }
            }

        # Serializar resultados
        resultados = []
        for patron in patrones:
            resultados.append({
                "id": patron.id,
                "concepto_normalizado": patron.concepto_normalizado,
                "tipo_patron": patron.tipo_patron.value,
                "monto_promedio": float(patron.monto_promedio),
                "coeficiente_variacion": float(patron.coeficiente_variacion),
                "puede_aprobar_auto": patron.puede_aprobar_auto == 1,
                "pagos_analizados": patron.pagos_analizados,
                "frecuencia_detectada": patron.frecuencia_detectada
            })

        # Calcular estadísticas del proveedor
        total_auto_aprobables = sum(1 for p in patrones if p.puede_aprobar_auto == 1)

        return {
            "success": True,
            "data": {
                "proveedor_id": proveedor_id,
                "proveedor_nombre": patrones[0].proveedor.razon_social if patrones[0].proveedor else None,
                "patrones": resultados,
                "total": len(patrones),
                "estadisticas": {
                    "auto_aprobables": total_auto_aprobables,
                    "porcentaje_automatizable": (total_auto_aprobables / len(patrones) * 100) if patrones else 0,
                    "tipo_a": sum(1 for p in patrones if p.tipo_patron == TipoPatron.TIPO_A),
                    "tipo_b": sum(1 for p in patrones if p.tipo_patron == TipoPatron.TIPO_B),
                    "tipo_c": sum(1 for p in patrones if p.tipo_patron == TipoPatron.TIPO_C)
                }
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo patrones del proveedor: {str(e)}"
        )
