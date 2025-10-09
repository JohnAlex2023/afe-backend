# app/services/automation/metrics_service.py
"""
Servicio de métricas en tiempo real para el sistema de automatización.

Calcula, actualiza y proporciona métricas agregadas sobre el rendimiento
del sistema de automatización.
"""

from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from app.models.automation_audit import AutomationAudit, AutomationMetrics, ProveedorTrust
from app.models.factura import Factura, EstadoFactura
from app.models.proveedor import Proveedor


class MetricsService:
    """
    Servicio para gestión de métricas del sistema de automatización.
    """

    def __init__(self):
        pass

    def calcular_metricas_tiempo_real(self, db: Session) -> Dict[str, Any]:
        """
        Calcula métricas en tiempo real del sistema.

        Returns:
            Diccionario con métricas actualizadas
        """
        ahora = datetime.utcnow()
        hoy = ahora.date()
        inicio_mes = date(ahora.year, ahora.month, 1)

        # Métricas del día
        metricas_dia = self._calcular_metricas_periodo(
            db, hoy, hoy + timedelta(days=1), "día"
        )

        # Métricas del mes
        metricas_mes = self._calcular_metricas_periodo(
            db, inicio_mes, hoy + timedelta(days=1), "mes"
        )

        # Métricas de últimas 24 horas
        hace_24h = ahora - timedelta(hours=24)
        metricas_24h = self._calcular_metricas_desde_timestamp(
            db, hace_24h, "últimas_24h"
        )

        # Top proveedores
        top_proveedores = self._obtener_top_proveedores(db, inicio_mes)

        # Tendencias
        tendencias = self._calcular_tendencias(db, dias=7)

        return {
            "timestamp": ahora.isoformat(),
            "dia_actual": metricas_dia,
            "mes_actual": metricas_mes,
            "ultimas_24h": metricas_24h,
            "top_proveedores": top_proveedores,
            "tendencias": tendencias,
            "salud_sistema": self._evaluar_salud_sistema(metricas_24h)
        }

    def _calcular_metricas_periodo(
        self,
        db: Session,
        fecha_inicio: date,
        fecha_fin: date,
        periodo_nombre: str
    ) -> Dict[str, Any]:
        """
        Calcula métricas para un período específico (por fecha).
        """
        # Auditorías del período
        audits = db.query(AutomationAudit).filter(
            and_(
                func.date(AutomationAudit.timestamp) >= fecha_inicio,
                func.date(AutomationAudit.timestamp) < fecha_fin
            )
        ).all()

        return self._agregar_metricas_desde_audits(audits, periodo_nombre)

    def _calcular_metricas_desde_timestamp(
        self,
        db: Session,
        timestamp_inicio: datetime,
        periodo_nombre: str
    ) -> Dict[str, Any]:
        """
        Calcula métricas desde un timestamp específico.
        """
        audits = db.query(AutomationAudit).filter(
            AutomationAudit.timestamp >= timestamp_inicio
        ).all()

        return self._agregar_metricas_desde_audits(audits, periodo_nombre)

    def _agregar_metricas_desde_audits(
        self,
        audits: List[AutomationAudit],
        periodo_nombre: str
    ) -> Dict[str, Any]:
        """
        Agrega métricas desde una lista de auditorías.
        """
        if not audits:
            return self._metricas_vacias(periodo_nombre)

        total_procesadas = len(audits)
        aprobadas_auto = sum(1 for a in audits if a.decision == 'aprobada_auto')
        en_revision = sum(1 for a in audits if a.decision == 'en_revision')
        rechazadas = sum(1 for a in audits if a.decision == 'rechazada')

        # Tasas
        tasa_automatizacion = (aprobadas_auto / total_procesadas * 100) if total_procesadas > 0 else 0

        # Calcular tasa de precisión (decisiones correctas)
        decisiones_correctas = sum(1 for a in audits
                                  if not a.override_manual and not a.requirio_accion_manual)
        tasa_precision = (decisiones_correctas / total_procesadas * 100) if total_procesadas > 0 else 0

        # Confianza promedio
        confianzas = [float(a.confianza) for a in audits if a.confianza is not None]
        confianza_promedio = sum(confianzas) / len(confianzas) if confianzas else 0

        # Tiempos de procesamiento
        tiempos = [a.tiempo_procesamiento_ms for a in audits if a.tiempo_procesamiento_ms is not None]
        tiempo_promedio = sum(tiempos) / len(tiempos) if tiempos else 0
        tiempo_min = min(tiempos) if tiempos else 0
        tiempo_max = max(tiempos) if tiempos else 0

        # Patrones detectados
        patrones = {}
        for audit in audits:
            patron = audit.patron_detectado or 'desconocido'
            patrones[patron] = patrones.get(patron, 0) + 1

        # Montos
        montos = [float(a.monto_factura) for a in audits if a.monto_factura is not None]
        monto_total = sum(montos)

        montos_aprobados = [float(a.monto_factura) for a in audits
                          if a.monto_factura is not None and a.decision == 'aprobada_auto']
        monto_total_aprobado = sum(montos_aprobados)

        return {
            "periodo": periodo_nombre,
            "total_procesadas": total_procesadas,
            "aprobadas_automaticamente": aprobadas_auto,
            "enviadas_revision": en_revision,
            "rechazadas": rechazadas,
            "tasa_automatizacion": round(tasa_automatizacion, 2),
            "tasa_precision": round(tasa_precision, 2),
            "confianza_promedio": round(confianza_promedio, 4),
            "tiempo_promedio_ms": round(tiempo_promedio, 2),
            "tiempo_min_ms": tiempo_min,
            "tiempo_max_ms": tiempo_max,
            "patrones_detectados": patrones,
            "monto_total_procesado": round(monto_total, 2),
            "monto_total_aprobado_auto": round(monto_total_aprobado, 2),
            "ahorro_tiempo_estimado_horas": round(total_procesadas * 0.25, 2)  # 15 min por factura
        }

    def _metricas_vacias(self, periodo_nombre: str) -> Dict[str, Any]:
        """Retorna estructura de métricas vacías."""
        return {
            "periodo": periodo_nombre,
            "total_procesadas": 0,
            "aprobadas_automaticamente": 0,
            "enviadas_revision": 0,
            "rechazadas": 0,
            "tasa_automatizacion": 0.0,
            "tasa_precision": 0.0,
            "confianza_promedio": 0.0,
            "tiempo_promedio_ms": 0,
            "tiempo_min_ms": 0,
            "tiempo_max_ms": 0,
            "patrones_detectados": {},
            "monto_total_procesado": 0.0,
            "monto_total_aprobado_auto": 0.0,
            "ahorro_tiempo_estimado_horas": 0.0
        }

    def _obtener_top_proveedores(
        self,
        db: Session,
        fecha_desde: date,
        limite: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Obtiene los proveedores con más facturas procesadas.
        """
        # Consulta agrupada
        resultados = db.query(
            AutomationAudit.proveedor_nit,
            AutomationAudit.proveedor_nombre,
            func.count(AutomationAudit.id).label('total_facturas'),
            func.sum(func.case([(AutomationAudit.decision == 'aprobada_auto', 1)], else_=0)).label('aprobadas_auto'),
            func.avg(AutomationAudit.confianza).label('confianza_promedio')
        ).filter(
            func.date(AutomationAudit.timestamp) >= fecha_desde
        ).group_by(
            AutomationAudit.proveedor_nit,
            AutomationAudit.proveedor_nombre
        ).order_by(
            desc('total_facturas')
        ).limit(limite).all()

        top_proveedores = []
        for r in resultados:
            tasa_auto = (r.aprobadas_auto / r.total_facturas * 100) if r.total_facturas > 0 else 0
            top_proveedores.append({
                "nit": r.proveedor_nit,
                "nombre": r.proveedor_nombre,
                "total_facturas": r.total_facturas,
                "aprobadas_automaticamente": r.aprobadas_auto,
                "tasa_automatizacion": round(tasa_auto, 2),
                "confianza_promedio": round(float(r.confianza_promedio or 0), 4)
            })

        return top_proveedores

    def _calcular_tendencias(
        self,
        db: Session,
        dias: int = 7
    ) -> Dict[str, Any]:
        """
        Calcula tendencias de los últimos N días.
        """
        hoy = datetime.utcnow().date()
        tendencias_diarias = []

        for i in range(dias):
            fecha = hoy - timedelta(days=i)
            metricas = self._calcular_metricas_periodo(
                db, fecha, fecha + timedelta(days=1), f"día_{i}"
            )
            tendencias_diarias.append({
                "fecha": fecha.isoformat(),
                "total_procesadas": metricas["total_procesadas"],
                "tasa_automatizacion": metricas["tasa_automatizacion"],
                "tasa_precision": metricas["tasa_precision"]
            })

        # Revertir para orden cronológico
        tendencias_diarias.reverse()

        # Calcular delta (comparar hoy con promedio de 7 días)
        if len(tendencias_diarias) > 1:
            ultima = tendencias_diarias[-1]
            promedio_anteriores = sum(t["total_procesadas"] for t in tendencias_diarias[:-1]) / (len(tendencias_diarias) - 1)
            delta_procesadas = ultima["total_procesadas"] - promedio_anteriores
        else:
            delta_procesadas = 0

        return {
            "dias_analizados": dias,
            "tendencia_diaria": tendencias_diarias,
            "delta_procesadas_vs_promedio": round(delta_procesadas, 2)
        }

    def _evaluar_salud_sistema(self, metricas_24h: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa la salud general del sistema basándose en métricas.
        """
        # Criterios de salud
        tasa_auto = metricas_24h.get("tasa_automatizacion", 0)
        tasa_precision = metricas_24h.get("tasa_precision", 0)
        total_procesadas = metricas_24h.get("total_procesadas", 0)

        # Determinar estado
        if tasa_auto >= 75 and tasa_precision >= 90:
            estado = "excelente"
            color = "green"
        elif tasa_auto >= 60 and tasa_precision >= 80:
            estado = "bueno"
            color = "blue"
        elif tasa_auto >= 40 and tasa_precision >= 70:
            estado = "moderado"
            color = "yellow"
        else:
            estado = "necesita_atencion"
            color = "red"

        # Alertas
        alertas = []
        if tasa_precision < 80:
            alertas.append("Tasa de precisión por debajo del objetivo (80%)")
        if tasa_auto < 50:
            alertas.append("Tasa de automatización baja (<50%)")
        if total_procesadas == 0:
            alertas.append("No se han procesado facturas en las últimas 24h")

        return {
            "estado": estado,
            "color": color,
            "score": round((tasa_auto * 0.4 + tasa_precision * 0.6), 2),
            "alertas": alertas,
            "recomendaciones": self._generar_recomendaciones(metricas_24h)
        }

    def _generar_recomendaciones(self, metricas: Dict[str, Any]) -> List[str]:
        """Genera recomendaciones basadas en métricas."""
        recomendaciones = []

        tasa_auto = metricas.get("tasa_automatizacion", 0)
        tasa_precision = metricas.get("tasa_precision", 0)

        if tasa_auto < 50:
            recomendaciones.append(
                "Considere reducir los umbrales de confianza para aumentar la tasa de automatización"
            )

        if tasa_precision < 80:
            recomendaciones.append(
                "Considere aumentar los umbrales de confianza para mejorar la precisión"
            )

        if metricas.get("total_procesadas", 0) == 0:
            recomendaciones.append(
                "Ejecute el procesamiento automático para procesar facturas pendientes"
            )

        return recomendaciones

    def actualizar_metricas_agregadas(self, db: Session, periodo: str = "daily") -> AutomationMetrics:
        """
        Actualiza las métricas agregadas en la base de datos.

        Args:
            db: Sesión de base de datos
            periodo: 'hourly' o 'daily'

        Returns:
            Registro de métricas creado/actualizado
        """
        ahora = datetime.utcnow()

        if periodo == "hourly":
            periodo_str = ahora.strftime("%Y-%m-%d-%H")
            fecha_inicio = ahora.replace(minute=0, second=0, microsecond=0)
            fecha_fin = fecha_inicio + timedelta(hours=1)
        else:  # daily
            periodo_str = ahora.strftime("%Y-%m-%d")
            fecha_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
            fecha_fin = fecha_inicio + timedelta(days=1)

        # Calcular métricas
        metricas = self._calcular_metricas_desde_timestamp(db, fecha_inicio, periodo_str)

        # Buscar o crear registro
        registro = db.query(AutomationMetrics).filter(
            AutomationMetrics.periodo == periodo_str
        ).first()

        if not registro:
            registro = AutomationMetrics(periodo=periodo_str)
            db.add(registro)

        # Actualizar valores
        registro.fecha_calculo = ahora
        registro.total_facturas_procesadas = metricas["total_procesadas"]
        registro.total_aprobadas_automaticamente = metricas["aprobadas_automaticamente"]
        registro.total_enviadas_revision = metricas["enviadas_revision"]
        registro.total_rechazadas = metricas["rechazadas"]
        registro.tasa_automatizacion = Decimal(str(metricas["tasa_automatizacion"]))
        registro.tasa_precision = Decimal(str(metricas["tasa_precision"]))
        registro.tiempo_promedio_procesamiento_ms = int(metricas["tiempo_promedio_ms"])
        registro.tiempo_minimo_procesamiento_ms = metricas["tiempo_min_ms"]
        registro.tiempo_maximo_procesamiento_ms = metricas["tiempo_max_ms"]
        registro.confianza_promedio = Decimal(str(metricas["confianza_promedio"]))
        registro.patrones_detectados = metricas["patrones_detectados"]
        registro.monto_total_procesado = Decimal(str(metricas["monto_total_procesado"]))
        registro.monto_total_aprobado_auto = Decimal(str(metricas["monto_total_aprobado_auto"]))

        db.commit()
        db.refresh(registro)

        return registro

    def actualizar_trust_score_proveedor(
        self,
        db: Session,
        proveedor_id: int
    ) -> ProveedorTrust:
        """
        Actualiza el score de confianza de un proveedor basándose en su historial.
        """
        # Obtener o crear registro de trust
        trust = db.query(ProveedorTrust).filter(
            ProveedorTrust.proveedor_id == proveedor_id
        ).first()

        if not trust:
            trust = ProveedorTrust(proveedor_id=proveedor_id)
            db.add(trust)

        # Obtener proveedor
        proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
        if not proveedor:
            return trust

        # Obtener facturas del proveedor
        facturas = db.query(Factura).filter(Factura.proveedor_id == proveedor_id).all()

        trust.total_facturas = len(facturas)
        trust.facturas_aprobadas = sum(
            1 for f in facturas if f.estado in [EstadoFactura.aprobada, EstadoFactura.aprobada_auto]
        )
        trust.facturas_rechazadas = sum(1 for f in facturas if f.estado == EstadoFactura.rechazada)
        trust.facturas_aprobadas_auto = sum(1 for f in facturas if f.estado == EstadoFactura.aprobada_auto)

        # Calcular tasas
        if trust.total_facturas > 0:
            trust.tasa_aprobacion = Decimal(trust.facturas_aprobadas / trust.total_facturas * 100)
            trust.tasa_automatizacion_exitosa = Decimal(
                trust.facturas_aprobadas_auto / trust.total_facturas * 100
            )
        else:
            trust.tasa_aprobacion = Decimal('0')
            trust.tasa_automatizacion_exitosa = Decimal('0')

        # Calcular trust score
        trust_score = self._calcular_trust_score(trust)
        trust.trust_score = Decimal(str(trust_score))

        # Determinar nivel
        if trust.bloqueado:
            trust.nivel_confianza = 'bloqueado'
        elif trust_score >= 0.85:
            trust.nivel_confianza = 'alto'
        elif trust_score >= 0.50:
            trust.nivel_confianza = 'medio'
        else:
            trust.nivel_confianza = 'bajo'

        db.commit()
        db.refresh(trust)

        return trust

    def _calcular_trust_score(self, trust: ProveedorTrust) -> float:
        """
        Calcula el score de confianza basándose en métricas del proveedor.
        """
        if trust.total_facturas == 0:
            return 0.5  # Score neutral para nuevos proveedores

        # Factores del score
        tasa_aprobacion = float(trust.tasa_aprobacion) / 100
        tasa_auto_exitosa = float(trust.tasa_automatizacion_exitosa) / 100

        # Peso por cantidad de facturas (más facturas = más confiable)
        factor_volumen = min(1.0, trust.total_facturas / 20)  # Máximo a 20 facturas

        # Calcular score ponderado
        score = (
            tasa_aprobacion * 0.5 +
            tasa_auto_exitosa * 0.3 +
            factor_volumen * 0.2
        )

        return max(0.0, min(1.0, score))
