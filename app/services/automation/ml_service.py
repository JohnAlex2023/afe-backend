# app/services/automation/ml_service.py
"""
Servicio de Machine Learning para el sistema de automatización (Fase 2).

Este módulo implementa capacidades de ML para:
- Aprendizaje de patrones por proveedor
- Predicción de anomalías
- Mejora continua con feedback
- Detección de fraude

NOTA: Esta es una implementación placeholder que incluye la arquitectura
y métodos básicos. La integración con modelos ML reales se realizará en Fase 2.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
import json

from app.models.automation_audit import AutomationAudit, ProveedorTrust
from app.models.factura import Factura, EstadoFactura


class MLPredictionResult:
    """Resultado de una predicción ML."""

    def __init__(
        self,
        score_confianza: float,
        prediccion: str,
        factores: Dict[str, float],
        anomalias_detectadas: List[str]
    ):
        self.score_confianza = score_confianza
        self.prediccion = prediccion
        self.factores = factores
        self.anomalias_detectadas = anomalias_detectadas


class MLService:
    """
    Servicio de Machine Learning para automatización inteligente.

    Fase 1 (Actual): Reglas heurísticas avanzadas
    Fase 2 (Futuro): Modelos ML entrenados (Random Forest, XGBoost, etc.)
    """

    def __init__(self):
        self.version = "1.0-heuristic"
        self.model_loaded = False

        # Configuración de umbrales para detección de anomalías
        self.anomaly_thresholds = {
            'monto_desviacion_max': 3.0,  # Desviaciones estándar
            'frecuencia_desviacion_max': 2.0,
            'score_anomalia_minimo': 0.7,
            'variacion_monto_critica': 50.0,  # Porcentaje
        }

    def predecir_aprobacion(
        self,
        db: Session,
        factura: Factura,
        facturas_historicas: List[Factura],
        metadata: Optional[Dict[str, Any]] = None
    ) -> MLPredictionResult:
        """
        Predice si una factura debería ser aprobada usando ML.

        En Fase 1, usa heurísticas avanzadas.
        En Fase 2, usará modelos entrenados.

        Args:
            db: Sesión de BD
            factura: Factura a evaluar
            facturas_historicas: Historial del proveedor
            metadata: Información adicional

        Returns:
            Resultado de la predicción con score de confianza
        """
        # Extraer características
        features = self._extraer_caracteristicas(factura, facturas_historicas)

        # Detectar anomalías
        anomalias = self._detectar_anomalias(factura, facturas_historicas, features)

        # Calcular score (heurístico por ahora)
        score = self._calcular_score_heuristico(features, anomalias)

        # Determinar predicción
        if score >= 0.85:
            prediccion = "aprobar"
        elif score >= 0.60:
            prediccion = "revisar"
        else:
            prediccion = "rechazar"

        # Factores que contribuyen al score
        factores = self._identificar_factores_decision(features, score)

        return MLPredictionResult(
            score_confianza=score,
            prediccion=prediccion,
            factores=factores,
            anomalias_detectadas=anomalias
        )

    def _extraer_caracteristicas(
        self,
        factura: Factura,
        facturas_historicas: List[Factura]
    ) -> Dict[str, Any]:
        """
        Extrae características relevantes para ML.
        """
        features = {}

        # Características de la factura actual
        features['monto'] = float(factura.total_a_pagar or 0)
        features['tiene_orden_compra'] = bool(factura.orden_compra_numero)
        features['dias_hasta_vencimiento'] = (
            (factura.fecha_vencimiento - factura.fecha_emision).days
            if factura.fecha_vencimiento else 0
        )

        # Características del proveedor
        if facturas_historicas:
            features['total_facturas_proveedor'] = len(facturas_historicas)

            montos = [float(f.total_a_pagar or 0) for f in facturas_historicas if f.total_a_pagar]
            if montos:
                features['monto_promedio_historico'] = sum(montos) / len(montos)
                features['monto_maximo_historico'] = max(montos)
                features['monto_minimo_historico'] = min(montos)

                # Variabilidad de montos
                if len(montos) > 1:
                    import statistics
                    features['desviacion_monto'] = statistics.stdev(montos)
                else:
                    features['desviacion_monto'] = 0

            # Tasa de aprobación histórica
            aprobadas = sum(
                1 for f in facturas_historicas
                if f.estado in [EstadoFactura.aprobada, EstadoFactura.aprobada_auto]
            )
            features['tasa_aprobacion_historica'] = aprobadas / len(facturas_historicas)

            # Días desde última factura
            if facturas_historicas:
                ultima_fecha = max(f.fecha_emision for f in facturas_historicas)
                features['dias_desde_ultima'] = (factura.fecha_emision - ultima_fecha).days

                # Calcular promedio de días entre facturas
                fechas = sorted([f.fecha_emision for f in facturas_historicas])
                if len(fechas) > 1:
                    diferencias = [(fechas[i] - fechas[i - 1]).days for i in range(1, len(fechas))]
                    features['promedio_dias_entre_facturas'] = sum(diferencias) / len(diferencias)
                else:
                    features['promedio_dias_entre_facturas'] = 0
        else:
            # Proveedor nuevo
            features['total_facturas_proveedor'] = 0
            features['tasa_aprobacion_historica'] = 0.5  # Neutral
            features['es_proveedor_nuevo'] = True

        # Características temporales
        features['dia_mes'] = factura.fecha_emision.day
        features['mes'] = factura.fecha_emision.month
        features['dia_semana'] = factura.fecha_emision.weekday()

        return features

    def _detectar_anomalias(
        self,
        factura: Factura,
        facturas_historicas: List[Factura],
        features: Dict[str, Any]
    ) -> List[str]:
        """
        Detecta anomalías en la factura usando técnicas estadísticas.
        """
        anomalias = []

        if not facturas_historicas:
            return anomalias  # No hay suficiente historial

        # 1. Anomalía en monto
        if 'monto_promedio_historico' in features and 'desviacion_monto' in features:
            monto_actual = features['monto']
            monto_promedio = features['monto_promedio_historico']
            desviacion = features['desviacion_monto']

            if desviacion > 0:
                z_score = abs(monto_actual - monto_promedio) / desviacion

                if z_score > self.anomaly_thresholds['monto_desviacion_max']:
                    anomalias.append(
                        f"Monto anómalo: {z_score:.1f} desviaciones estándar del promedio"
                    )

        # 2. Anomalía en frecuencia
        if 'dias_desde_ultima' in features and 'promedio_dias_entre_facturas' in features:
            dias_desde_ultima = features['dias_desde_ultima']
            promedio_dias = features['promedio_dias_entre_facturas']

            if promedio_dias > 0:
                # Factura demasiado pronto o demasiado tarde
                if dias_desde_ultima < promedio_dias * 0.5:
                    anomalias.append(
                        f"Factura muy temprana: {dias_desde_ultima} días vs {promedio_dias:.0f} promedio"
                    )
                elif dias_desde_ultima > promedio_dias * 1.5:
                    anomalias.append(
                        f"Factura tardía: {dias_desde_ultima} días vs {promedio_dias:.0f} promedio"
                    )

        # 3. Monto excesivamente alto
        if 'monto_maximo_historico' in features:
            monto_actual = features['monto']
            monto_max = features['monto_maximo_historico']

            if monto_max > 0:
                variacion_pct = ((monto_actual - monto_max) / monto_max) * 100
                if variacion_pct > self.anomaly_thresholds['variacion_monto_critica']:
                    anomalias.append(
                        f"Monto {variacion_pct:.1f}% mayor que el máximo histórico"
                    )

        # 4. Patrón de fechas inusual
        dia_actual = features['dia_mes']
        dias_historicos = [f.fecha_emision.day for f in facturas_historicas]

        # Calcular promedio de día del mes
        if dias_historicos:
            promedio_dia = sum(dias_historicos) / len(dias_historicos)
            if abs(dia_actual - promedio_dia) > 7:  # Más de 7 días de diferencia
                anomalias.append(
                    f"Día del mes inusual: día {dia_actual} vs promedio día {promedio_dia:.0f}"
                )

        return anomalias

    def _calcular_score_heuristico(
        self,
        features: Dict[str, Any],
        anomalias: List[str]
    ) -> float:
        """
        Calcula un score de confianza usando heurísticas.
        En Fase 2, esto será reemplazado por un modelo ML entrenado.
        """
        score = 0.5  # Base neutral

        # Factor: Historial del proveedor
        if features.get('total_facturas_proveedor', 0) >= 5:
            score += 0.15
        elif features.get('total_facturas_proveedor', 0) >= 3:
            score += 0.10

        # Factor: Tasa de aprobación histórica
        tasa_aprobacion = features.get('tasa_aprobacion_historica', 0)
        if tasa_aprobacion >= 0.9:
            score += 0.20
        elif tasa_aprobacion >= 0.7:
            score += 0.10

        # Factor: Tiene orden de compra
        if features.get('tiene_orden_compra', False):
            score += 0.10

        # Factor: Monto razonable
        if 'monto_promedio_historico' in features:
            monto_actual = features['monto']
            monto_promedio = features['monto_promedio_historico']
            if monto_promedio > 0:
                variacion_pct = abs((monto_actual - monto_promedio) / monto_promedio) * 100
                if variacion_pct <= 10:
                    score += 0.15
                elif variacion_pct <= 20:
                    score += 0.08

        # Penalización por anomalías
        score -= len(anomalias) * 0.15

        # Penalización por proveedor nuevo
        if features.get('es_proveedor_nuevo', False):
            score -= 0.20

        return max(0.0, min(1.0, score))

    def _identificar_factores_decision(
        self,
        features: Dict[str, Any],
        score: float
    ) -> Dict[str, float]:
        """
        Identifica qué factores contribuyeron más a la decisión.
        """
        factores = {}

        if features.get('total_facturas_proveedor', 0) >= 3:
            factores['historial_proveedor'] = 0.15

        tasa_aprobacion = features.get('tasa_aprobacion_historica', 0)
        if tasa_aprobacion > 0:
            factores['tasa_aprobacion'] = tasa_aprobacion * 0.20

        if features.get('tiene_orden_compra', False):
            factores['orden_compra'] = 0.10

        if 'monto_promedio_historico' in features:
            monto_actual = features['monto']
            monto_promedio = features['monto_promedio_historico']
            if monto_promedio > 0:
                variacion_pct = abs((monto_actual - monto_promedio) / monto_promedio) * 100
                factores['consistencia_monto'] = max(0, 0.15 * (1 - variacion_pct / 100))

        return factores

    def entrenar_modelo(
        self,
        db: Session,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> Dict[str, Any]:
        """
        Entrena el modelo ML con datos históricos.

        FASE 2: Implementará entrenamiento real de modelos.
        FASE 1: Placeholder que retorna estadísticas.
        """
        # Obtener datos de entrenamiento
        audits = db.query(AutomationAudit).filter(
            and_(
                AutomationAudit.timestamp >= fecha_inicio,
                AutomationAudit.timestamp < fecha_fin
            )
        ).all()

        if not audits:
            return {
                "exito": False,
                "mensaje": "No hay datos suficientes para entrenamiento",
                "total_registros": 0
            }

        # Estadísticas de los datos
        total_registros = len(audits)
        aprobadas = sum(1 for a in audits if a.decision == 'aprobada_auto')
        rechazadas = sum(1 for a in audits if a.decision == 'rechazada')
        revision = sum(1 for a in audits if a.decision == 'en_revision')

        # En Fase 2, aquí iría el código de entrenamiento real
        # Ejemplo:
        # X, y = self._preparar_datos_entrenamiento(audits)
        # self.model = RandomForestClassifier()
        # self.model.fit(X, y)
        # self.model_loaded = True

        return {
            "exito": True,
            "mensaje": "Modelo entrenado (modo heurístico - Fase 1)",
            "version": self.version,
            "total_registros": total_registros,
            "distribucion": {
                "aprobadas": aprobadas,
                "rechazadas": rechazadas,
                "revision": revision
            },
            "nota": "En Fase 2 se implementará entrenamiento de modelos ML reales"
        }

    def feedback_decision(
        self,
        db: Session,
        audit_id: int,
        resultado_real: str,
        feedback: Optional[str] = None
    ) -> bool:
        """
        Registra feedback sobre una decisión automática.
        Usado para mejorar el modelo (Fase 2).

        Args:
            audit_id: ID del registro de auditoría
            resultado_real: 'correcto' | 'incorrecto' | 'parcial'
            feedback: Comentarios adicionales

        Returns:
            True si se registró exitosamente
        """
        audit = db.query(AutomationAudit).filter(
            AutomationAudit.id == audit_id
        ).first()

        if not audit:
            return False

        # Actualizar resultado final
        if resultado_real == 'correcto':
            audit.resultado_final = 'confirmado'
        elif resultado_real == 'incorrecto':
            audit.resultado_final = 'revertido'
        else:
            audit.resultado_final = 'modificado'

        # Agregar feedback a metadata
        if not audit.metadata:
            audit.metadata = {}

        audit.metadata['feedback'] = {
            'resultado': resultado_real,
            'comentario': feedback,
            'timestamp': datetime.utcnow().isoformat()
        }

        db.commit()

        # En Fase 2, este feedback se usará para reentrenamiento
        # self._actualizar_modelo_con_feedback(audit)

        return True

    def detectar_fraude(
        self,
        db: Session,
        factura: Factura,
        facturas_historicas: List[Factura]
    ) -> Tuple[float, List[str]]:
        """
        Detecta posibles indicadores de fraude.

        Returns:
            (score_fraude, indicadores)
            score_fraude: 0.0 (sin riesgo) - 1.0 (alto riesgo)
            indicadores: Lista de señales de alerta
        """
        indicadores = []
        score_fraude = 0.0

        # 1. Monto inusualmente alto
        if facturas_historicas:
            montos = [float(f.total_a_pagar or 0) for f in facturas_historicas if f.total_a_pagar]
            if montos:
                monto_actual = float(factura.total_a_pagar or 0)
                monto_max = max(montos)

                if monto_actual > monto_max * 2:
                    indicadores.append("Monto más del doble del máximo histórico")
                    score_fraude += 0.3

        # 2. Factura duplicada sospechosa
        for f_hist in facturas_historicas:
            if (f_hist.numero_factura == factura.numero_factura and
                    f_hist.id != factura.id):
                indicadores.append("Posible número de factura duplicado")
                score_fraude += 0.5

        # 3. CUFE duplicado
        for f_hist in facturas_historicas:
            if f_hist.cufe == factura.cufe and f_hist.id != factura.id:
                indicadores.append("CUFE duplicado detectado")
                score_fraude += 0.8

        # 4. Patrón de fechas sospechoso
        if factura.fecha_emision > datetime.now().date():
            indicadores.append("Fecha de emisión en el futuro")
            score_fraude += 0.4

        # 5. Vencimiento muy corto
        if factura.fecha_vencimiento:
            dias_vencimiento = (factura.fecha_vencimiento - factura.fecha_emision).days
            if dias_vencimiento < 0:
                indicadores.append("Fecha de vencimiento anterior a emisión")
                score_fraude += 0.6
            elif dias_vencimiento > 365:
                indicadores.append("Vencimiento inusualmente largo (>1 año)")
                score_fraude += 0.2

        return (min(1.0, score_fraude), indicadores)

    def obtener_estadisticas_modelo(self) -> Dict[str, Any]:
        """
        Retorna estadísticas del modelo actual.
        """
        return {
            "version": self.version,
            "tipo": "heuristic" if not self.model_loaded else "ml",
            "modelo_cargado": self.model_loaded,
            "nota_fase2": "En Fase 2 se implementarán modelos ML (Random Forest, XGBoost, etc.)"
        }
