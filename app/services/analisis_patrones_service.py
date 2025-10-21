"""
Servicio de Análisis Continuo de Patrones de Facturas.

Este servicio enterprise:
1. Analiza facturas de la BD (últimos N meses)
2. Agrupa por proveedor + concepto normalizado
3. Calcula estadísticas actualizadas (promedio, desviación, CV)
4. Clasifica en TIPO_A, TIPO_B, TIPO_C
5. Actualiza/inserta en historial_pagos
6. Se ejecuta periódicamente (diario/semanal) o bajo demanda

Este es el componente de PRODUCCIÓN que reemplaza al bootstrap inicial del Excel.

Nivel: Enterprise Fortune 500
Autor: Sistema de Automatización AFE
Fecha: 2025-10-08
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
from collections import defaultdict
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.factura import Factura, EstadoFactura
from app.models.historial_pagos import HistorialPagos, TipoPatron
from app.models.proveedor import Proveedor


# Configurar logging
logger = logging.getLogger(__name__)


class AnalizadorPatronesService:
    """
    Servicio empresarial de análisis continuo de patrones de facturas.

    Características:
    - Análisis incremental (solo facturas relevantes)
    - Clasificación automática TIPO_A/B/C
    - Actualización inteligente de patrones existentes
    - Detección de cambios en comportamiento de proveedores
    - Métricas de calidad y confiabilidad
    """

    # Umbrales de clasificación (según especificación)
    UMBRAL_TIPO_A = Decimal('5.0')   # CV < 5% = Valor fijo
    UMBRAL_TIPO_B = Decimal('30.0')  # CV < 30% = Valor fluctuante predecible
    # CV > 30% = TIPO_C (excepcional)

    # Configuración de análisis
    MIN_FACTURAS_PATRON = 3  # Mínimo de facturas para considerar un patrón válido
    MIN_MESES_DIFERENTES = 2  # Mínimo de meses diferentes con facturas

    def __init__(self, db: Session):
        """
        Inicializa el servicio.

        Args:
            db: Sesión de base de datos SQLAlchemy
        """
        self.db = db
        self.stats = {
            'facturas_analizadas': 0,
            'patrones_detectados': 0,
            'patrones_nuevos': 0,
            'patrones_actualizados': 0,
            'patrones_mejorados': 0,  # Patrones que mejoraron de TIPO_C a TIPO_B/A
            'patrones_degradados': 0,  # Patrones que empeoraron
            'errores': 0
        }

    def analizar_patrones_desde_bd(
        self,
        ventana_meses: int = 12,
        solo_proveedores: Optional[List[int]] = None,
        estados_facturas: Optional[List[EstadoFactura]] = None,
        forzar_recalculo: bool = False
    ) -> Dict[str, Any]:
        """
        Analiza facturas de la BD y actualiza patrones en historial_pagos.

        Args:
            ventana_meses: Cantidad de meses hacia atrás a analizar (default: 12)
            solo_proveedores: Lista de IDs de proveedores a analizar (None = todos)
            estados_facturas: Estados de facturas a considerar (None = aprobadas y pagadas)
            forzar_recalculo: Si True, recalcula todos los patrones incluso si ya existen

        Returns:
            Diccionario con resultados del análisis
        """
        logger.info(f"Iniciando análisis de patrones desde BD (ventana: {ventana_meses} meses)")

        try:
            # 1. Obtener facturas relevantes
            fecha_desde = datetime.now() - timedelta(days=ventana_meses * 30)

            if estados_facturas is None:
                estados_facturas = [EstadoFactura.aprobada, EstadoFactura.aprobada_auto]

            facturas = self._obtener_facturas_para_analisis(
                fecha_desde=fecha_desde,
                solo_proveedores=solo_proveedores,
                estados=estados_facturas
            )

            logger.info(f"     {len(facturas)} facturas obtenidas para análisis")
            self.stats['facturas_analizadas'] = len(facturas)

            if len(facturas) < self.MIN_FACTURAS_PATRON:
                logger.warning("Insuficientes facturas para análisis de patrones")
                return self._generar_resultado(exito=False, mensaje="Insuficientes facturas")

            # 2. Agrupar facturas por proveedor + concepto
            grupos = self._agrupar_facturas_por_patron(facturas)
            logger.info(f"     {len(grupos)} grupos de patrones detectados")

            # 3. Calcular estadísticas para cada grupo
            patrones_calculados = self._calcular_estadisticas_grupos(grupos, ventana_meses)
            logger.info(f"     Estadísticas calculadas para {len(patrones_calculados)} patrones")

            # 4. Persistir o actualizar patrones
            self._persistir_patrones(patrones_calculados, forzar_recalculo)
            logger.info(f"     Patrones persistidos: {self.stats['patrones_nuevos']} nuevos, {self.stats['patrones_actualizados']} actualizados")

            # 5. Analizar cambios en patrones existentes
            cambios_detectados = self._detectar_cambios_patrones(patrones_calculados)

            return self._generar_resultado(
                exito=True,
                mensaje="Análisis completado exitosamente",
                cambios_detectados=cambios_detectados
            )

        except Exception as e:
            logger.error(f"Error en análisis de patrones: {str(e)}")
            return self._generar_resultado(
                exito=False,
                mensaje=f"Error: {str(e)}"
            )

    def _obtener_facturas_para_analisis(
        self,
        fecha_desde: datetime,
        solo_proveedores: Optional[List[int]],
        estados: List[EstadoFactura]
    ) -> List[Factura]:
        """
        Obtiene facturas de la BD que cumplen criterios para análisis.
        """
        query = self.db.query(Factura).filter(
            Factura.fecha_emision >= fecha_desde.date(),
            Factura.estado.in_(estados),
            Factura.total_a_pagar.isnot(None),
            Factura.total_a_pagar > 0,
            Factura.proveedor_id.isnot(None)
        )

        if solo_proveedores:
            query = query.filter(Factura.proveedor_id.in_(solo_proveedores))

        # Ordenar por fecha para análisis temporal
        facturas = query.order_by(Factura.fecha_emision.asc()).all()

        return facturas

    def _agrupar_facturas_por_patron(self, facturas: List[Factura]) -> Dict[str, List[Factura]]:
        """
        Agrupa facturas por proveedor + concepto normalizado.

        Estrategia de agrupación:
        1. Si existe concepto_normalizado → usar ese
        2. Si existe concepto_hash → usar ese
        3. Si no → generar hash del concepto_principal
        """
        grupos = defaultdict(list)

        for factura in facturas:
            # Obtener o generar concepto normalizado
            concepto_normalizado = self._obtener_concepto_normalizado(factura)

            if not concepto_normalizado:
                # Si no hay concepto, agrupar solo por proveedor (patrón genérico)
                concepto_normalizado = "servicio_general"

            # Generar clave única: proveedor_id|concepto_normalizado
            key = f"{factura.proveedor_id}|{concepto_normalizado}"
            grupos[key].append(factura)

        # Filtrar grupos que no cumplan mínimos
        grupos_validos = {
            key: facturas_grupo
            for key, facturas_grupo in grupos.items()
            if len(facturas_grupo) >= self.MIN_FACTURAS_PATRON
        }

        return grupos_validos

    def _obtener_concepto_normalizado(self, factura: Factura) -> Optional[str]:
        """
        Obtiene o genera el concepto normalizado de una factura.
        """
        # Prioridad 1: concepto_normalizado existente
        if factura.concepto_normalizado:
            return factura.concepto_normalizado.lower().strip()

        # Prioridad 2: generar desde concepto_principal
        if factura.concepto_principal:
            concepto = factura.concepto_principal.lower().strip()
            # Normalizar: quitar acentos, caracteres especiales
            concepto = concepto.replace('á', 'a').replace('é', 'e').replace('í', 'i')
            concepto = concepto.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
            return concepto[:200]  # Limitar longitud

        # Si no hay concepto, retornar None
        return None

    def _calcular_estadisticas_grupos(
        self,
        grupos: Dict[str, List[Factura]],
        ventana_meses: int
    ) -> List[Dict[str, Any]]:
        """
        Calcula estadísticas detalladas para cada grupo de facturas.
        """
        patrones_calculados = []

        for key, facturas_grupo in grupos.items():
            try:
                proveedor_id_str, concepto_normalizado = key.split('|', 1)
                proveedor_id = int(proveedor_id_str)

                # Extraer montos y fechas
                montos = [float(f.total_a_pagar) for f in facturas_grupo if f.total_a_pagar]
                fechas = [f.fecha_emision for f in facturas_grupo]

                if len(montos) < self.MIN_FACTURAS_PATRON:
                    continue

                # Calcular meses únicos
                meses_unicos = set((f.year, f.month) for f in fechas)

                if len(meses_unicos) < self.MIN_MESES_DIFERENTES:
                    continue

                # Estadísticas básicas
                monto_promedio = Decimal(str(statistics.mean(montos)))
                monto_minimo = Decimal(str(min(montos)))
                monto_maximo = Decimal(str(max(montos)))
                desviacion_std = Decimal(str(statistics.stdev(montos))) if len(montos) > 1 else Decimal('0')

                # Coeficiente de variación (CV%)
                cv = (desviacion_std / monto_promedio * 100) if monto_promedio > 0 else Decimal('0')

                # Clasificar tipo de patrón
                if cv < self.UMBRAL_TIPO_A:
                    tipo_patron = TipoPatron.TIPO_A
                elif cv < self.UMBRAL_TIPO_B:
                    tipo_patron = TipoPatron.TIPO_B
                else:
                    tipo_patron = TipoPatron.TIPO_C

                # Análisis de frecuencia temporal
                frecuencia_detectada = self._detectar_frecuencia_temporal(fechas)

                # Determinar si puede aprobar automáticamente
                puede_aprobar_auto = self._puede_aprobar_automaticamente(
                    tipo_patron=tipo_patron,
                    cantidad_facturas=len(facturas_grupo),
                    meses_diferentes=len(meses_unicos),
                    cv=cv
                )

                # Calcular rangos para TIPO_B
                rango_inferior = None
                rango_superior = None
                if tipo_patron == TipoPatron.TIPO_B:
                    rango_inferior = max(Decimal('0'), monto_promedio - (2 * desviacion_std))
                    rango_superior = monto_promedio + (2 * desviacion_std)

                # Umbral de alerta
                umbral_alerta = self._calcular_umbral_alerta(tipo_patron, cv)

                # Generar hash del concepto
                concepto_hash = hashlib.md5(concepto_normalizado.encode('utf-8')).hexdigest()

                # Última factura (para tracking)
                ultima_factura = max(facturas_grupo, key=lambda f: f.fecha_emision)

                # Construir patrón
                patron = {
                    'proveedor_id': proveedor_id,
                    'concepto_normalizado': concepto_normalizado,
                    'concepto_hash': concepto_hash,
                    'tipo_patron': tipo_patron,
                    'pagos_analizados': len(facturas_grupo),
                    'meses_con_pagos': len(meses_unicos),
                    'monto_promedio': monto_promedio,
                    'monto_minimo': monto_minimo,
                    'monto_maximo': monto_maximo,
                    'desviacion_estandar': desviacion_std,
                    'coeficiente_variacion': cv,
                    'rango_inferior': rango_inferior,
                    'rango_superior': rango_superior,
                    'frecuencia_detectada': frecuencia_detectada,
                    'ultimo_pago_fecha': ultima_factura.fecha_emision,
                    'ultimo_pago_monto': ultima_factura.total_a_pagar,
                    'puede_aprobar_auto': 1 if puede_aprobar_auto else 0,
                    'umbral_alerta': umbral_alerta,
                    'facturas_ids': [f.id for f in facturas_grupo],
                    'ventana_meses': ventana_meses
                }

                patrones_calculados.append(patron)
                self.stats['patrones_detectados'] += 1

            except Exception as e:
                logger.error(f"Error calculando estadísticas para grupo {key}: {str(e)}")
                self.stats['errores'] += 1

        return patrones_calculados

    def _detectar_frecuencia_temporal(self, fechas: List[datetime]) -> str:
        """
        Detecta la frecuencia temporal del patrón (mensual, quincenal, etc).
        """
        if len(fechas) < 2:
            return "unica"

        # Calcular diferencias entre fechas consecutivas
        fechas_ordenadas = sorted(fechas)
        diferencias_dias = [
            (fechas_ordenadas[i+1] - fechas_ordenadas[i]).days
            for i in range(len(fechas_ordenadas) - 1)
        ]

        if not diferencias_dias:
            return "unica"

        promedio_dias = statistics.mean(diferencias_dias)

        # Clasificar frecuencia
        if promedio_dias <= 10:
            return "semanal"
        elif promedio_dias <= 20:
            return "quincenal"
        elif promedio_dias <= 35:
            return "mensual"
        elif promedio_dias <= 65:
            return "bimestral"
        elif promedio_dias <= 100:
            return "trimestral"
        elif promedio_dias <= 200:
            return "semestral"
        else:
            return "anual"

    def _puede_aprobar_automaticamente(
        self,
        tipo_patron: TipoPatron,
        cantidad_facturas: int,
        meses_diferentes: int,
        cv: Decimal
    ) -> bool:
        """
        Determina si un patrón cumple criterios para aprobación automática.

        Criterios:
        - TIPO_A: Siempre aprobable si tiene ≥3 facturas
        - TIPO_B: Aprobable si tiene ≥5 facturas y CV < 25%
        - TIPO_C: Nunca aprobable automáticamente
        """
        if tipo_patron == TipoPatron.TIPO_A:
            return cantidad_facturas >= 3 and meses_diferentes >= 2

        elif tipo_patron == TipoPatron.TIPO_B:
            return cantidad_facturas >= 5 and meses_diferentes >= 3 and cv < 25

        else:  # TIPO_C
            return False

    def _calcular_umbral_alerta(self, tipo_patron: TipoPatron, cv: Decimal) -> Decimal:
        """
        Calcula el umbral de alerta para desviaciones.
        """
        if tipo_patron == TipoPatron.TIPO_A:
            return Decimal('15.0')  # 15% para valores fijos
        elif tipo_patron == TipoPatron.TIPO_B:
            return min(Decimal('30.0'), cv + Decimal('10.0'))  # Dinámico según CV
        else:  # TIPO_C
            return Decimal('50.0')  # 50% para valores excepcionales

    def _persistir_patrones(
        self,
        patrones: List[Dict[str, Any]],
        forzar_recalculo: bool
    ) -> None:
        """
        Persiste o actualiza patrones en historial_pagos.
        """
        for patron in patrones:
            try:
                # Buscar patrón existente
                patron_existente = self.db.query(HistorialPagos).filter(
                    HistorialPagos.proveedor_id == patron['proveedor_id'],
                    HistorialPagos.concepto_hash == patron['concepto_hash']
                ).first()

                if patron_existente:
                    # Verificar si hay cambios significativos
                    if forzar_recalculo or self._hay_cambios_significativos(patron_existente, patron):
                        self._actualizar_patron(patron_existente, patron)
                        self.stats['patrones_actualizados'] += 1

                        # Detectar mejoras/degradaciones
                        if patron_existente.tipo_patron != patron['tipo_patron']:
                            if self._es_mejora_patron(patron_existente.tipo_patron, patron['tipo_patron']):
                                self.stats['patrones_mejorados'] += 1
                            else:
                                self.stats['patrones_degradados'] += 1
                else:
                    # Crear nuevo patrón
                    self._crear_patron(patron)
                    self.stats['patrones_nuevos'] += 1

                # Commit cada 20 patrones
                if (self.stats['patrones_nuevos'] + self.stats['patrones_actualizados']) % 20 == 0:
                    self.db.commit()

            except Exception as e:
                self.db.rollback()
                logger.error(f"Error persistiendo patrón: {str(e)}")
                self.stats['errores'] += 1

        # Commit final
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en commit final: {str(e)}")

    def _hay_cambios_significativos(
        self,
        patron_existente: HistorialPagos,
        patron_nuevo: Dict[str, Any]
    ) -> bool:
        """
        Determina si hay cambios significativos entre el patrón existente y el nuevo.
        """
        # Cambio en tipo de patrón
        if patron_existente.tipo_patron != patron_nuevo['tipo_patron']:
            return True

        # Cambio significativo en monto promedio (>10%)
        if patron_existente.monto_promedio > 0:
            variacion_monto = abs(
                float(patron_nuevo['monto_promedio'] - patron_existente.monto_promedio) /
                float(patron_existente.monto_promedio)
            ) * 100

            if variacion_monto > 10:
                return True

        # Cambio en cantidad de pagos (nuevos datos)
        if patron_nuevo['pagos_analizados'] > patron_existente.pagos_analizados:
            return True

        # Cambio en aprobabilidad automática
        if patron_nuevo['puede_aprobar_auto'] != patron_existente.puede_aprobar_auto:
            return True

        return False

    def _es_mejora_patron(self, tipo_anterior: TipoPatron, tipo_nuevo: TipoPatron) -> bool:
        """Determina si el cambio de tipo de patrón es una mejora."""
        jerarquia = {TipoPatron.TIPO_A: 3, TipoPatron.TIPO_B: 2, TipoPatron.TIPO_C: 1}
        return jerarquia[tipo_nuevo] > jerarquia[tipo_anterior]

    def _crear_patron(self, patron: Dict[str, Any]) -> None:
        """Crea un nuevo registro en historial_pagos."""
        nuevo_patron = HistorialPagos(
            proveedor_id=patron['proveedor_id'],
            concepto_normalizado=patron['concepto_normalizado'],
            concepto_hash=patron['concepto_hash'],
            tipo_patron=patron['tipo_patron'],
            pagos_analizados=patron['pagos_analizados'],
            meses_con_pagos=patron['meses_con_pagos'],
            monto_promedio=patron['monto_promedio'],
            monto_minimo=patron['monto_minimo'],
            monto_maximo=patron['monto_maximo'],
            desviacion_estandar=patron['desviacion_estandar'],
            coeficiente_variacion=patron['coeficiente_variacion'],
            rango_inferior=patron['rango_inferior'],
            rango_superior=patron['rango_superior'],
            frecuencia_detectada=patron['frecuencia_detectada'],
            ultimo_pago_fecha=patron['ultimo_pago_fecha'],
            ultimo_pago_monto=patron['ultimo_pago_monto'],
            puede_aprobar_auto=patron['puede_aprobar_auto'],
            umbral_alerta=patron['umbral_alerta'],
            fecha_analisis=datetime.utcnow(),
            version_algoritmo="2.0"  # Versión de producción
        )

        self.db.add(nuevo_patron)

    def _actualizar_patron(self, patron_existente: HistorialPagos, patron_nuevo: Dict[str, Any]) -> None:
        """Actualiza un patrón existente con nuevos datos."""
        patron_existente.tipo_patron = patron_nuevo['tipo_patron']
        patron_existente.pagos_analizados = patron_nuevo['pagos_analizados']
        patron_existente.meses_con_pagos = patron_nuevo['meses_con_pagos']
        patron_existente.monto_promedio = patron_nuevo['monto_promedio']
        patron_existente.monto_minimo = patron_nuevo['monto_minimo']
        patron_existente.monto_maximo = patron_nuevo['monto_maximo']
        patron_existente.desviacion_estandar = patron_nuevo['desviacion_estandar']
        patron_existente.coeficiente_variacion = patron_nuevo['coeficiente_variacion']
        patron_existente.rango_inferior = patron_nuevo['rango_inferior']
        patron_existente.rango_superior = patron_nuevo['rango_superior']
        patron_existente.frecuencia_detectada = patron_nuevo['frecuencia_detectada']
        patron_existente.ultimo_pago_fecha = patron_nuevo['ultimo_pago_fecha']
        patron_existente.ultimo_pago_monto = patron_nuevo['ultimo_pago_monto']
        patron_existente.puede_aprobar_auto = patron_nuevo['puede_aprobar_auto']
        patron_existente.umbral_alerta = patron_nuevo['umbral_alerta']
        patron_existente.fecha_analisis = datetime.utcnow()
        patron_existente.version_algoritmo = "2.0"

    def _detectar_cambios_patrones(self, patrones: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detecta y reporta cambios significativos en los patrones."""
        return {
            'patrones_mejorados': self.stats['patrones_mejorados'],
            'patrones_degradados': self.stats['patrones_degradados'],
            'nuevos_auto_aprobables': sum(
                1 for p in patrones
                if p['puede_aprobar_auto'] == 1 and p.get('es_nuevo', False)
            )
        }

    def _generar_resultado(
        self,
        exito: bool,
        mensaje: str,
        cambios_detectados: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Genera el resultado final del análisis."""
        resultado = {
            'exito': exito,
            'mensaje': mensaje,
            'timestamp': datetime.utcnow().isoformat(),
            'estadisticas': self.stats.copy()
        }

        if cambios_detectados:
            resultado['cambios_detectados'] = cambios_detectados

        # Calcular métricas de calidad
        if self.stats['patrones_detectados'] > 0:
            resultado['metricas_calidad'] = {
                'porcentaje_auto_aprobables': (
                    (self.stats['patrones_nuevos'] + self.stats['patrones_actualizados']) /
                    self.stats['patrones_detectados'] * 100
                ),
                'tasa_errores': (
                    self.stats['errores'] / self.stats['facturas_analizadas'] * 100
                ) if self.stats['facturas_analizadas'] > 0 else 0
            }

        return resultado

    def obtener_estadisticas_patrones(self, proveedor_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas globales de patrones en historial_pagos.

        Args:
            proveedor_id: Si se especifica, filtra por proveedor

        Returns:
            Estadísticas de los patrones almacenados
        """
        query = self.db.query(HistorialPagos)

        if proveedor_id:
            query = query.filter(HistorialPagos.proveedor_id == proveedor_id)

        patrones = query.all()

        if not patrones:
            return {
                'total': 0,
                'por_tipo': {},
                'auto_aprobables': 0
            }

        # Contar por tipo
        tipo_a = sum(1 for p in patrones if p.tipo_patron == TipoPatron.TIPO_A)
        tipo_b = sum(1 for p in patrones if p.tipo_patron == TipoPatron.TIPO_B)
        tipo_c = sum(1 for p in patrones if p.tipo_patron == TipoPatron.TIPO_C)

        auto_aprobables = sum(1 for p in patrones if p.puede_aprobar_auto == 1)

        return {
            'total': len(patrones),
            'por_tipo': {
                'TIPO_A': tipo_a,
                'TIPO_B': tipo_b,
                'TIPO_C': tipo_c
            },
            'auto_aprobables': auto_aprobables,
            'porcentaje_automatizable': (auto_aprobables / len(patrones) * 100) if patrones else 0,
            'proveedores_unicos': len(set(p.proveedor_id for p in patrones))
        }
