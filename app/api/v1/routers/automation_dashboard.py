# app/api/v1/routers/automation_dashboard.py
"""
Router para el Dashboard de Control del Sistema de Automatización.

Proporciona endpoints para:
- Métricas en tiempo real
- Control y configuración
- Override manual de decisiones
- Monitoreo de salud del sistema
- Gestión de trust de proveedores
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.services.automation.metrics_service import MetricsService
from app.services.automation.ml_service import MLService
from app.models.automation_audit import AutomationAudit, ProveedorTrust, ConfiguracionAutomatizacion
from app.models.factura import Factura, EstadoFactura
from app.crud import factura as crud_factura
from app.schemas.common import ResponseBase


router = APIRouter(tags=["Dashboard de Automatización"])

# Instanciar servicios
metrics_service = MetricsService()
ml_service = MLService()


# ==================== SCHEMAS ====================

class DashboardMetrics(BaseModel):
    """Métricas del dashboard."""
    timestamp: datetime
    dia_actual: Dict[str, Any]
    mes_actual: Dict[str, Any]
    ultimas_24h: Dict[str, Any]
    top_proveedores: List[Dict[str, Any]]
    tendencias: Dict[str, Any]
    salud_sistema: Dict[str, Any]


class OverrideRequest(BaseModel):
    """Solicitud de override manual."""
    factura_id: int
    nueva_decision: str = Field(..., pattern="^(aprobada|rechazada|en_revision)$")
    motivo: str
    usuario: str


class FeedbackRequest(BaseModel):
    """Feedback sobre una decisión automática."""
    audit_id: int
    resultado: str = Field(..., pattern="^(correcto|incorrecto|parcial)$")
    comentario: Optional[str] = None


class TrustScoreUpdate(BaseModel):
    """Actualización manual de trust score."""
    proveedor_id: int
    nuevo_score: float = Field(..., ge=0.0, le=1.0)
    motivo: str
    usuario: str


class ConfigUpdate(BaseModel):
    """Actualización de configuración."""
    clave: str
    valor: Any
    usuario: str


# ==================== ENDPOINTS DE DASHBOARD ====================

@router.get("/dashboard/metricas", response_model=DashboardMetrics)
async def obtener_metricas_dashboard(db: Session = Depends(get_db)):
    """
    Obtiene métricas en tiempo real para el dashboard.

    Incluye:
    - Estadísticas del día actual
    - Estadísticas del mes actual
    - Métricas de últimas 24 horas
    - Top proveedores
    - Tendencias
    - Salud del sistema
    """
    try:
        metricas = metrics_service.calcular_metricas_tiempo_real(db)
        return DashboardMetrics(**metricas)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo métricas del dashboard: {str(e)}"
        )


@router.get("/dashboard/salud")
async def obtener_salud_sistema(db: Session = Depends(get_db)):
    """
    Evalúa y retorna la salud general del sistema de automatización.

    Returns:
        - estado: 'excelente' | 'bueno' | 'moderado' | 'necesita_atencion'
        - score: Puntuación de 0-100
        - alertas: Lista de alertas activas
        - recomendaciones: Acciones sugeridas
    """
    try:
        metricas = metrics_service.calcular_metricas_tiempo_real(db)
        salud = metricas.get("salud_sistema", {})

        return ResponseBase(
            success=True,
            message="Salud del sistema evaluada",
            data=salud
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error evaluando salud del sistema: {str(e)}"
        )


@router.get("/dashboard/actividad-reciente")
async def obtener_actividad_reciente(
    limite: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Obtiene la actividad reciente del sistema (últimas decisiones).
    """
    try:
        # Obtener últimas auditorías
        audits = db.query(AutomationAudit).order_by(
            AutomationAudit.timestamp.desc()
        ).limit(limite).all()

        actividades = []
        for audit in audits:
            actividades.append({
                "id": audit.id,
                "timestamp": audit.timestamp.isoformat(),
                "factura_id": audit.factura_id,
                "decision": audit.decision,
                "confianza": float(audit.confianza),
                "motivo": audit.motivo,
                "patron": audit.patron_detectado,
                "proveedor": audit.proveedor_nombre,
                "monto": float(audit.monto_factura or 0),
                "requirio_accion_manual": audit.requirio_accion_manual,
                "override": audit.override_manual
            })

        return ResponseBase(
            success=True,
            message=f"Últimas {len(actividades)} actividades",
            data={"actividades": actividades}
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo actividad reciente: {str(e)}"
        )


@router.get("/dashboard/alertas")
async def obtener_alertas_activas(db: Session = Depends(get_db)):
    """
    Obtiene alertas activas del sistema.

    Alertas incluyen:
    - Facturas con anomalías detectadas
    - Decisiones con baja confianza pendientes
    - Proveedores bloqueados
    - Tasa de automatización baja
    """
    try:
        alertas = []

        # 1. Facturas pendientes con baja confianza
        facturas_baja_confianza = db.query(Factura).filter(
            and_(
                Factura.estado == EstadoFactura.en_revision,
                Factura.confianza_automatica < 0.5
            )
        ).limit(10).all()

        if facturas_baja_confianza:
            alertas.append({
                "tipo": "facturas_baja_confianza",
                "severidad": "media",
                "cantidad": len(facturas_baja_confianza),
                "mensaje": f"{len(facturas_baja_confianza)} facturas en revisión con baja confianza",
                "accion_sugerida": "Revisar y aprobar/rechazar manualmente"
            })

        # 2. Proveedores bloqueados
        proveedores_bloqueados = db.query(ProveedorTrust).filter(
            ProveedorTrust.bloqueado == True
        ).count()

        if proveedores_bloqueados > 0:
            alertas.append({
                "tipo": "proveedores_bloqueados",
                "severidad": "alta",
                "cantidad": proveedores_bloqueados,
                "mensaje": f"{proveedores_bloqueados} proveedores bloqueados",
                "accion_sugerida": "Revisar motivos de bloqueo"
            })

        # 3. Auditorías con override recientes
        hace_24h = datetime.utcnow() - timedelta(hours=24)
        overrides_recientes = db.query(AutomationAudit).filter(
            and_(
                AutomationAudit.override_manual == True,
                AutomationAudit.timestamp >= hace_24h
            )
        ).count()

        if overrides_recientes > 5:
            alertas.append({
                "tipo": "muchos_overrides",
                "severidad": "media",
                "cantidad": overrides_recientes,
                "mensaje": f"{overrides_recientes} overrides manuales en 24h",
                "accion_sugerida": "Revisar configuración de umbrales"
            })

        # 4. Salud del sistema
        metricas = metrics_service.calcular_metricas_tiempo_real(db)
        salud = metricas.get("salud_sistema", {})

        if salud.get("estado") == "necesita_atencion":
            alertas.extend([{
                "tipo": "salud_sistema",
                "severidad": "alta",
                "mensaje": alerta,
                "accion_sugerida": "Ver recomendaciones del sistema"
            } for alerta in salud.get("alertas", [])])

        return ResponseBase(
            success=True,
            message=f"{len(alertas)} alertas activas",
            data={
                "total_alertas": len(alertas),
                "alertas": alertas
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo alertas: {str(e)}"
        )


# ==================== ENDPOINTS DE CONTROL ====================

@router.post("/control/override")
async def aplicar_override_manual(
    request: OverrideRequest,
    db: Session = Depends(get_db)
):
    """
    Aplica un override manual a una decisión automática.

    Permite a un usuario autorizado cambiar la decisión tomada
    automáticamente por el sistema.
    """
    try:
        # Obtener factura
        factura = crud_factura.get_factura(db, request.factura_id)
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")

        # Obtener auditoría más reciente de esta factura
        audit = db.query(AutomationAudit).filter(
            AutomationAudit.factura_id == request.factura_id
        ).order_by(AutomationAudit.timestamp.desc()).first()

        # Actualizar estado de factura
        decision_map = {
            "aprobada": EstadoFactura.aprobada,
            "rechazada": EstadoFactura.rechazada,
            "en_revision": EstadoFactura.en_revision
        }

        factura.estado = decision_map[request.nueva_decision]

        # Si hay auditoría, marcar override
        if audit:
            audit.override_manual = True
            audit.override_por = request.usuario
            audit.override_razon = request.motivo
            audit.override_fecha = datetime.utcnow()
            audit.requirio_accion_manual = True

        db.commit()

        return ResponseBase(
            success=True,
            message=f"Override aplicado: factura {request.factura_id} → {request.nueva_decision}",
            data={
                "factura_id": request.factura_id,
                "decision_anterior": audit.decision if audit else "desconocida",
                "decision_nueva": request.nueva_decision,
                "aplicado_por": request.usuario,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error aplicando override: {str(e)}"
        )


@router.post("/control/feedback")
async def registrar_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db)
):
    """
    Registra feedback sobre una decisión automática.

    El feedback se usa para mejorar el modelo ML en Fase 2.
    """
    try:
        exito = ml_service.feedback_decision(
            db=db,
            audit_id=request.audit_id,
            resultado_real=request.resultado,
            feedback=request.comentario
        )

        if not exito:
            raise HTTPException(
                status_code=404,
                detail="Auditoría no encontrada"
            )

        return ResponseBase(
            success=True,
            message="Feedback registrado exitosamente",
            data={
                "audit_id": request.audit_id,
                "resultado": request.resultado,
                "uso_futuro": "Este feedback se usará para mejorar el modelo ML en Fase 2"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error registrando feedback: {str(e)}"
        )


@router.post("/control/actualizar-trust")
async def actualizar_trust_score(
    request: TrustScoreUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza manualmente el trust score de un proveedor.
    """
    try:
        # Obtener o crear trust record
        trust = db.query(ProveedorTrust).filter(
            ProveedorTrust.proveedor_id == request.proveedor_id
        ).first()

        if not trust:
            trust = ProveedorTrust(proveedor_id=request.proveedor_id)
            db.add(trust)

        # Actualizar score
        score_anterior = float(trust.trust_score)
        trust.trust_score = request.nuevo_score

        # Determinar nivel
        if request.nuevo_score >= 0.85:
            trust.nivel_confianza = 'alto'
        elif request.nuevo_score >= 0.50:
            trust.nivel_confianza = 'medio'
        else:
            trust.nivel_confianza = 'bajo'

        # Registrar en metadata
        if not trust.historial_confianza:
            trust.historial_confianza = []

        trust.historial_confianza.append({
            "fecha": datetime.utcnow().isoformat(),
            "score_anterior": score_anterior,
            "score_nuevo": float(request.nuevo_score),
            "motivo": request.motivo,
            "usuario": request.usuario,
            "tipo": "manual"
        })

        db.commit()
        db.refresh(trust)

        return ResponseBase(
            success=True,
            message=f"Trust score actualizado para proveedor {request.proveedor_id}",
            data={
                "proveedor_id": request.proveedor_id,
                "score_anterior": score_anterior,
                "score_nuevo": float(trust.trust_score),
                "nivel": trust.nivel_confianza
            }
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando trust score: {str(e)}"
        )


@router.post("/control/bloquear-proveedor/{proveedor_id}")
async def bloquear_proveedor(
    proveedor_id: int,
    motivo: str = Body(...),
    usuario: str = Body(...),
    db: Session = Depends(get_db)
):
    """
    Bloquea un proveedor de aprobaciones automáticas.
    """
    try:
        trust = db.query(ProveedorTrust).filter(
            ProveedorTrust.proveedor_id == proveedor_id
        ).first()

        if not trust:
            trust = ProveedorTrust(proveedor_id=proveedor_id)
            db.add(trust)

        trust.bloqueado = True
        trust.motivo_bloqueo = motivo
        trust.bloqueado_por = usuario
        trust.bloqueado_en = datetime.utcnow()
        trust.nivel_confianza = 'bloqueado'

        db.commit()

        return ResponseBase(
            success=True,
            message=f"Proveedor {proveedor_id} bloqueado",
            data={
                "proveedor_id": proveedor_id,
                "bloqueado": True,
                "motivo": motivo,
                "bloqueado_por": usuario
            }
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error bloqueando proveedor: {str(e)}"
        )


@router.post("/control/desbloquear-proveedor/{proveedor_id}")
async def desbloquear_proveedor(
    proveedor_id: int,
    usuario: str = Body(...),
    db: Session = Depends(get_db)
):
    """
    Desbloquea un proveedor previamente bloqueado.
    """
    try:
        trust = db.query(ProveedorTrust).filter(
            ProveedorTrust.proveedor_id == proveedor_id
        ).first()

        if not trust:
            raise HTTPException(
                status_code=404,
                detail="Proveedor no encontrado en trust records"
            )

        trust.bloqueado = False
        trust.motivo_bloqueo = None

        # Recalcular nivel basándose en score
        if trust.trust_score >= 0.85:
            trust.nivel_confianza = 'alto'
        elif trust.trust_score >= 0.50:
            trust.nivel_confianza = 'medio'
        else:
            trust.nivel_confianza = 'bajo'

        db.commit()

        return ResponseBase(
            success=True,
            message=f"Proveedor {proveedor_id} desbloqueado",
            data={
                "proveedor_id": proveedor_id,
                "bloqueado": False,
                "nivel_confianza": trust.nivel_confianza
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error desbloqueando proveedor: {str(e)}"
        )


# ==================== ENDPOINTS DE CONFIGURACIÓN ====================

@router.get("/config/parametros")
async def obtener_parametros_configuracion(db: Session = Depends(get_db)):
    """
    Obtiene todos los parámetros de configuración del sistema.
    """
    try:
        configs = db.query(ConfiguracionAutomatizacion).filter(
            ConfiguracionAutomatizacion.activa == True
        ).all()

        parametros = {}
        for config in configs:
            categoria = config.categoria or "general"
            if categoria not in parametros:
                parametros[categoria] = {}

            parametros[categoria][config.clave] = {
                "valor": config.valor,
                "tipo": config.tipo_dato,
                "descripcion": config.descripcion,
                "version": config.version
            }

        return ResponseBase(
            success=True,
            message=f"{len(configs)} parámetros de configuración",
            data=parametros
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo configuración: {str(e)}"
        )


@router.put("/config/parametro")
async def actualizar_parametro(
    request: ConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza un parámetro de configuración.
    """
    try:
        config = db.query(ConfiguracionAutomatizacion).filter(
            ConfiguracionAutomatizacion.clave == request.clave
        ).first()

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Parámetro '{request.clave}' no encontrado"
            )

        # Guardar valor anterior en metadata
        if not config.metadata:
            config.metadata = {}

        if 'historial' not in config.metadata:
            config.metadata['historial'] = []

        config.metadata['historial'].append({
            "valor_anterior": config.valor,
            "valor_nuevo": request.valor,
            "usuario": request.usuario,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Actualizar
        config.valor = request.valor
        config.actualizado_por = request.usuario
        config.actualizado_en = datetime.utcnow()
        config.version += 1

        db.commit()

        return ResponseBase(
            success=True,
            message=f"Parámetro '{request.clave}' actualizado",
            data={
                "clave": request.clave,
                "valor": request.valor,
                "version": config.version
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando parámetro: {str(e)}"
        )


# ==================== ENDPOINTS DE REPORTES ====================

@router.get("/reportes/resumen-periodo")
async def generar_resumen_periodo(
    fecha_inicio: str = Query(..., description="Formato: YYYY-MM-DD"),
    fecha_fin: str = Query(..., description="Formato: YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    Genera un resumen ejecutivo del período especificado.
    """
    try:
        from datetime import datetime

        inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

        metricas = metrics_service._calcular_metricas_periodo(
            db, inicio, fin + timedelta(days=1), f"{fecha_inicio}_a_{fecha_fin}"
        )

        # Calcular ROI (ahorro de tiempo)
        tiempo_ahorrado_horas = metricas.get("ahorro_tiempo_estimado_horas", 0)
        costo_hora_humana = 50000  # COP (ajustable)
        ahorro_estimado = tiempo_ahorrado_horas * costo_hora_humana

        resumen = {
            "periodo": {
                "inicio": fecha_inicio,
                "fin": fecha_fin,
                "dias": (fin - inicio).days + 1
            },
            "rendimiento": {
                "total_procesadas": metricas["total_procesadas"],
                "aprobadas_automaticamente": metricas["aprobadas_automaticamente"],
                "tasa_automatizacion": metricas["tasa_automatizacion"],
                "tasa_precision": metricas["tasa_precision"]
            },
            "roi": {
                "tiempo_ahorrado_horas": tiempo_ahorrado_horas,
                "ahorro_estimado_cop": ahorro_estimado,
                "costo_hora_base": costo_hora_humana
            },
            "financiero": {
                "monto_total_procesado": metricas["monto_total_procesado"],
                "monto_aprobado_automaticamente": metricas["monto_total_aprobado_auto"]
            },
            "patrones": metricas.get("patrones_detectados", {})
        }

        return ResponseBase(
            success=True,
            message="Resumen ejecutivo generado",
            data=resumen
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Formato de fecha inválido. Use YYYY-MM-DD"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando resumen: {str(e)}"
        )
