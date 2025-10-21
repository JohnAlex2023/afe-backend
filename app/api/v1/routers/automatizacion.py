# app/api/v1/routers/automatizacion.py
"""
Router para endpoints de automatización de facturas.

Proporciona endpoints para:
- Ejecutar procesamiento automático de facturas
- Configurar parámetros de automatización
- Obtener métricas y estadísticas
- Ver historial de decisiones automáticas
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, Field
from datetime import datetime

from app.db.session import get_db
from app.core.security import get_current_responsable
from app.services.automation.automation_service import AutomationService
from app.models.factura import Factura, EstadoFactura
from app.schemas.common import ResponseBase


router = APIRouter(tags=["Automatización"])


# ==================== SCHEMAS ====================

class ConfiguracionAutomatizacion(BaseModel):
    """Configuración de parámetros de automatización."""
    tolerancia_porcentaje: float = Field(
        default=5.0,
        ge=0.0,
        le=100.0,
        description="Porcentaje de tolerancia en diferencia de montos (0-100%)"
    )
    limite_facturas: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Número máximo de facturas a procesar por ejecución"
    )
    modo_debug: bool = Field(
        default=False,
        description="Incluir información detallada de debug"
    )


class ResultadoProcesamiento(BaseModel):
    """Resultado del procesamiento automático."""
    facturas_procesadas: int
    aprobadas_automaticamente: int
    enviadas_revision: int
    errores: int
    tasa_automatizacion: float
    tiempo_procesamiento_segundos: Optional[float] = None


# ==================== ENDPOINTS ====================

@router.post("/automatizacion/procesar")
async def procesar_facturas_automaticamente(
    config: ConfiguracionAutomatizacion = Body(default=ConfiguracionAutomatizacion()),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """
    🤖 Ejecuta el procesamiento automático de facturas pendientes.

    Este endpoint procesa facturas en estado 'en_revision' o 'pendiente'
    y las aprueba automáticamente si cumplen con los criterios de comparación
    con el mes anterior.

    **Criterios de aprobación automática:**
    - Existe factura del mismo proveedor y concepto en el mes anterior
    - Diferencia de monto <= tolerancia_porcentaje (default 5%)
    - Factura del mes anterior está aprobada

    **Parámetros configurables:**
    - `tolerancia_porcentaje`: % de diferencia permitida (default: 5%)
    - `limite_facturas`: Máximo de facturas a procesar (default: 50)
    - `modo_debug`: Incluir información detallada (default: false)

    **Respuesta:**
    ```json
    {
        "success": true,
        "message": "Procesadas 45 facturas. 12 aprobadas automáticamente.",
        "data": {
            "facturas_procesadas": 45,
            "aprobadas_automaticamente": 12,
            "enviadas_revision": 33,
            "errores": 0,
            "tasa_automatizacion": 26.67,
            "detalle_facturas": [...]
        }
    }
    ```

    **Logs de auditoría:**
    Todas las decisiones quedan registradas en el sistema de auditoría
    con información completa sobre el motivo de aprobación/rechazo.
    """
    try:
        # Validar permisos (solo admin puede ejecutar automatización)
        if hasattr(current_user, 'role') and current_user.role.nombre != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Solo administradores pueden ejecutar la automatización"
            )

        # Crear servicio de automatización
        automation_service = AutomationService()

        # TODO: Configurar tolerancia desde parámetros
        # Por ahora está hardcodeada en 5% en automation_service

        # Ejecutar procesamiento
        resultado = automation_service.procesar_facturas_pendientes(
            db=db,
            limite_facturas=config.limite_facturas,
            modo_debug=config.modo_debug
        )

        # Preparar respuesta
        mensaje = (
            f"Procesadas {resultado['facturas_procesadas']} facturas. "
            f"{resultado['aprobadas_automaticamente']} aprobadas automáticamente, "
            f"{resultado['enviadas_revision']} enviadas a revisión."
        )

        if resultado['errores'] > 0:
            mensaje += f" {resultado['errores']} errores."

        return ResponseBase(
            success=True,
            message=mensaje,
            data={
                **resultado['resumen_general'],
                'detalle_facturas': resultado.get('facturas_procesadas_detalle', [])
                if config.modo_debug else None
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando automatización: {str(e)}"
        )


@router.get("/automatizacion/estadisticas")
async def obtener_estadisticas_automatizacion(
    dias: int = Query(default=30, ge=1, le=365, description="Días hacia atrás"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """
    Obtiene estadísticas de automatización de los últimos N días.

    **Métricas incluidas:**
    - Total de facturas procesadas automáticamente
    - Tasa de aprobación automática
    - Tasa de precisión (aprobaciones correctas)
    - Distribución por método de decisión
    - Proveedores con mayor automatización

    **Respuesta:**
    ```json
    {
        "periodo": {"desde": "2025-09-08", "hasta": "2025-10-08", "dias": 30},
        "totales": {
            "procesadas": 150,
            "aprobadas_auto": 45,
            "enviadas_revision": 105,
            "tasa_automatizacion": 30.0
        },
        "por_metodo": {
            "comparacion_mes_anterior": 42,
            "patron_recurrencia": 3
        }
    }
    ```
    """
    try:
        from datetime import timedelta

        # Calcular rango de fechas
        fecha_hasta = datetime.utcnow()
        fecha_desde = fecha_hasta - timedelta(days=dias)

        # Consultar facturas procesadas automáticamente en el periodo
        facturas_procesadas = db.query(Factura).filter(
            Factura.fecha_procesamiento_auto >= fecha_desde,
            Factura.fecha_procesamiento_auto <= fecha_hasta
        ).all()

        # Calcular estadísticas
        total_procesadas = len(facturas_procesadas)
        aprobadas_auto = sum(
            1 for f in facturas_procesadas
            if f.estado == EstadoFactura.aprobada_auto
        )
        enviadas_revision = total_procesadas - aprobadas_auto

        tasa_automatizacion = (
            (aprobadas_auto / total_procesadas * 100)
            if total_procesadas > 0 else 0
        )

        # Contar por método de aprobación
        metodos = {}
        for factura in facturas_procesadas:
            if factura.procesamiento_info and isinstance(factura.procesamiento_info, dict):
                metodo = factura.procesamiento_info.get('metodo_aprobacion', 'otro')
                metodos[metodo] = metodos.get(metodo, 0) + 1

        return ResponseBase(
            success=True,
            message=f"Estadísticas de {dias} días",
            data={
                "periodo": {
                    "desde": fecha_desde.date().isoformat(),
                    "hasta": fecha_hasta.date().isoformat(),
                    "dias": dias
                },
                "totales": {
                    "procesadas": total_procesadas,
                    "aprobadas_auto": aprobadas_auto,
                    "enviadas_revision": enviadas_revision,
                    "tasa_automatizacion": round(tasa_automatizacion, 2)
                },
                "por_metodo": metodos
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@router.get("/automatizacion/facturas-pendientes")
async def listar_facturas_pendientes_procesamiento(
    limite: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """
     Lista facturas pendientes de procesamiento automático.

    Muestra facturas en estado 'en_revision' o 'pendiente' que aún
    no han sido procesadas por el sistema de automatización.

    **Parámetros:**
    - `limite`: Número máximo de facturas a retornar (1-500)

    **Respuesta:**
    Incluye información de cada factura pendiente:
    - Datos básicos (número, fecha, monto)
    - Proveedor
    - Si tiene factura del mes anterior
    - Diferencia estimada de monto
    """
    try:
        from app.crud import factura as crud_factura

        # Obtener facturas pendientes
        facturas_pendientes = db.query(Factura).filter(
            or_(
                Factura.estado == EstadoFactura.en_revision,
                Factura.estado == EstadoFactura.pendiente
            ),
            Factura.fecha_procesamiento_auto.is_(None)  # No procesadas aún
        ).limit(limite).all()

        # Preparar detalles de cada factura
        facturas_info = []
        for factura in facturas_pendientes:
            # Buscar factura del mes anterior
            factura_anterior = crud_factura.find_factura_mes_anterior(
                db=db,
                proveedor_id=factura.proveedor_id,
                fecha_actual=factura.fecha_emision,
                concepto_hash=factura.concepto_hash,
                concepto_normalizado=factura.concepto_normalizado
            )

            info = {
                "id": factura.id,
                "numero_factura": factura.numero_factura,
                "fecha_emision": factura.fecha_emision.isoformat() if factura.fecha_emision else None,
                "total": float(factura.total_a_pagar or 0),
                "proveedor_id": factura.proveedor_id,
                "proveedor_nombre": factura.proveedor.nombre if factura.proveedor else None,
                "estado": factura.estado.value if hasattr(factura.estado, 'value') else str(factura.estado),
                "tiene_mes_anterior": factura_anterior is not None
            }

            if factura_anterior:
                diferencia_pct = abs(
                    (float(factura.total_a_pagar) - float(factura_anterior.total_a_pagar)) /
                    float(factura_anterior.total_a_pagar) * 100
                ) if factura_anterior.total_a_pagar else 0

                info["mes_anterior"] = {
                    "id": factura_anterior.id,
                    "numero": factura_anterior.numero_factura,
                    "total": float(factura_anterior.total_a_pagar or 0),
                    "diferencia_porcentaje": round(diferencia_pct, 2),
                    "aprobacion_estimada": "SI" if diferencia_pct <= 5.0 else "NO"
                }

            facturas_info.append(info)

        return ResponseBase(
            success=True,
            message=f"{len(facturas_info)} facturas pendientes de procesamiento",
            data={
                "total": len(facturas_info),
                "facturas": facturas_info
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listando facturas pendientes: {str(e)}"
        )


@router.post("/automatizacion/procesar-factura/{factura_id}")
async def procesar_factura_individual(
    factura_id: int,
    modo_debug: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """
     Procesa una factura individual para aprobación automática.

    Permite probar la automatización con una factura específica.
    Útil para validar el comportamiento antes de procesar en lote.

    **Parámetros:**
    - `factura_id`: ID de la factura a procesar
    - `modo_debug`: Incluir información detallada de debug

    **Respuesta:**
    Incluye decisión tomada, confianza, criterios evaluados y explicación.
    """
    try:
        from app.crud import factura as crud_factura

        # Obtener factura
        factura = crud_factura.get_factura(db, factura_id)
        if not factura:
            raise HTTPException(
                status_code=404,
                detail=f"Factura {factura_id} no encontrada"
            )

        # Procesar con servicio de automatización
        automation_service = AutomationService()
        resultado = automation_service.procesar_factura_individual(
            db=db,
            factura=factura,
            modo_debug=modo_debug
        )

        return ResponseBase(
            success=resultado.get('procesado_exitosamente', False),
            message=f"Factura procesada: {resultado.get('decision', 'error')}",
            data=resultado
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando factura: {str(e)}"
        )
