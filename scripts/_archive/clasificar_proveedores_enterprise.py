"""
Script Enterprise: Clasificación Automática de Proveedores
===========================================================

Clasifica proveedores según análisis estadístico de sus facturas históricas.


Fecha: 2025-10-15

FUNCIONALIDAD:
--------------
1. Analiza historial de facturas de cada proveedor (6+ meses)
2. Calcula Coeficiente de Variación (CV) de montos
3. Clasifica en TipoServicioProveedor según CV:
   - CV < 15%: SERVICIO_FIJO_MENSUAL
   - CV 15-80%: SERVICIO_VARIABLE_PREDECIBLE
   - CV > 80%: SERVICIO_POR_CONSUMO
   - Sin recurrencia: SERVICIO_EVENTUAL

4. Determina NivelConfianzaProveedor según antigüedad:
   - 24+ meses: NIVEL_1_CRITICO o NIVEL_2_ALTO
   - 12-24 meses: NIVEL_2_ALTO o NIVEL_3_MEDIO
   - 6-12 meses: NIVEL_3_MEDIO
   - 3-6 meses: NIVEL_4_BAJO
   - <3 meses: NIVEL_5_NUEVO

5. Detecta si requiere orden de compra obligatoria

EJECUCIÓN:
----------
    python -m scripts.clasificar_proveedores_enterprise

    Argumentos opcionales:
    --dry-run: Muestra clasificación sin guardar en BD
    --verbose: Muestra análisis detallado
    --nit: Clasifica solo un NIT específico
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from statistics import mean, stdev

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.factura import Factura, EstadoFactura
from app.models.proveedor import Proveedor
from app.models.workflow_aprobacion import (
    AsignacionNitResponsable,
    TipoServicioProveedor,
    NivelConfianzaProveedor
)


class ClasificadorProveedoresEnterprise:
    """
    Clasificador automático de proveedores basado en análisis estadístico.

    Nivel: Fortune 500 Risk Management
    """

    def __init__(self, db: Session, verbose: bool = False):
        self.db = db
        self.verbose = verbose

        # Umbrales de clasificación (configurables)
        self.UMBRALES_CV = {
            'fijo': 15.0,              # CV < 15% → Servicio fijo
            'variable': 80.0,          # CV 15-80% → Variable predecible
            # CV > 80% → Por consumo
        }

        self.UMBRALES_ANTIGUEDAD = {
            'critico': 730,      # 24 meses
            'alto': 365,         # 12 meses
            'medio': 180,        # 6 meses
            'bajo': 90,          # 3 meses
        }

        self.MIN_FACTURAS_RECURRENTE = 3
        self.MIN_MESES_CON_FACTURAS = 3

    def clasificar_todos_proveedores(self, dry_run: bool = False) -> Dict[str, any]:
        """
        Clasifica todos los proveedores con asignación activa.

        Args:
            dry_run: Si True, no guarda cambios en BD

        Returns:
            Resumen de clasificación
        """
        print("=" * 80)
        print("CLASIFICACIÓN ENTERPRISE DE PROVEEDORES")
        print("=" * 80)
        print()

        # Obtener todas las asignaciones activas
        asignaciones = self.db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == True
        ).all()

        print(f"Total de asignaciones activas: {len(asignaciones)}")
        print()

        resultados = {
            'total_procesados': 0,
            'clasificados': 0,
            'sin_historial': 0,
            'errores': 0,
            'clasificacion': {
                'fijo': 0,
                'variable': 0,
                'consumo': 0,
                'eventual': 0
            }
        }

        for asignacion in asignaciones:
            try:
                resultado = self.clasificar_proveedor(asignacion.nit, dry_run)

                resultados['total_procesados'] += 1

                if resultado['clasificado']:
                    resultados['clasificados'] += 1
                    tipo = resultado['tipo_servicio']

                    if tipo == TipoServicioProveedor.SERVICIO_FIJO_MENSUAL:
                        resultados['clasificacion']['fijo'] += 1
                    elif tipo == TipoServicioProveedor.SERVICIO_VARIABLE_PREDECIBLE:
                        resultados['clasificacion']['variable'] += 1
                    elif tipo == TipoServicioProveedor.SERVICIO_POR_CONSUMO:
                        resultados['clasificacion']['consumo'] += 1
                    else:
                        resultados['clasificacion']['eventual'] += 1
                else:
                    resultados['sin_historial'] += 1

            except Exception as e:
                print(f"ERROR procesando NIT {asignacion.nit}: {e}")
                resultados['errores'] += 1

        # Mostrar resumen
        print()
        print("=" * 80)
        print("RESUMEN DE CLASIFICACIÓN")
        print("=" * 80)
        print(f"Total procesados:               {resultados['total_procesados']}")
        print(f"Clasificados exitosamente:      {resultados['clasificados']}")
        print(f"Sin historial suficiente:       {resultados['sin_historial']}")
        print(f"Errores:                        {resultados['errores']}")
        print()
        print("DISTRIBUCIÓN POR TIPO:")
        print(f"  Servicio Fijo:                {resultados['clasificacion']['fijo']}")
        print(f"  Variable Predecible:          {resultados['clasificacion']['variable']}")
        print(f"  Por Consumo:                  {resultados['clasificacion']['consumo']}")
        print(f"  Eventual:                     {resultados['clasificacion']['eventual']}")
        print()

        if not dry_run:
            print("Cambios guardados en base de datos")
        else:
            print("DRY RUN: Cambios NO guardados")

        return resultados

    def clasificar_proveedor(
        self,
        nit: str,
        dry_run: bool = False
    ) -> Dict[str, any]:
        """
        Clasifica un proveedor específico.

        Args:
            nit: NIT del proveedor
            dry_run: Si True, no guarda cambios

        Returns:
            Resultado de clasificación
        """
        # Obtener asignación
        asignacion = self.db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.nit == nit
        ).first()

        if not asignacion:
            return {
                'clasificado': False,
                'razon': 'NIT sin asignación'
            }

        # Obtener proveedor
        proveedor = self.db.query(Proveedor).filter(
            Proveedor.nit == nit
        ).first()

        if not proveedor:
            return {
                'clasificado': False,
                'razon': 'Proveedor no encontrado'
            }

        # Analizar historial de facturas (últimos 12 meses)
        fecha_limite = datetime.now() - timedelta(days=365)

        facturas = self.db.query(Factura).filter(
            Factura.proveedor_id == proveedor.id,
            Factura.fecha_emision >= fecha_limite,
            Factura.estado.in_([
                EstadoFactura.aprobada,
                EstadoFactura.aprobada_auto,
                EstadoFactura.pagada,
                EstadoFactura.en_revision
            ])
        ).all()

        if len(facturas) < self.MIN_FACTURAS_RECURRENTE:
            if self.verbose:
                print(f"ADVERTENCIA {nit} ({asignacion.nombre_proveedor}): "
                      f"Solo {len(facturas)} facturas, mínimo {self.MIN_FACTURAS_RECURRENTE}")

            # Clasificar como SERVICIO_EVENTUAL si no hay historial
            if not dry_run:
                asignacion.tipo_servicio_proveedor = TipoServicioProveedor.SERVICIO_EVENTUAL
                asignacion.nivel_confianza_proveedor = NivelConfianzaProveedor.NIVEL_5_NUEVO
                asignacion.coeficiente_variacion_historico = None
                asignacion.requiere_orden_compra_obligatoria = True
                self.db.commit()

            return {
                'clasificado': True,
                'tipo_servicio': TipoServicioProveedor.SERVICIO_EVENTUAL,
                'nivel_confianza': NivelConfianzaProveedor.NIVEL_5_NUEVO,
                'razon': 'Sin historial suficiente'
            }

        # Calcular estadísticas
        analisis = self._analizar_facturas(facturas)

        # Determinar tipo de servicio según CV
        tipo_servicio = self._determinar_tipo_servicio(analisis['cv'])

        # Determinar nivel de confianza según antigüedad
        nivel_confianza = self._determinar_nivel_confianza(
            analisis['antiguedad_dias'],
            tipo_servicio,
            analisis['cv']
        )

        # Determinar si requiere OC obligatoria
        requiere_oc = self._requiere_orden_compra_obligatoria(
            tipo_servicio,
            analisis['cv'],
            analisis['monto_promedio']
        )

        # Mostrar resultado
        if self.verbose or True:  # Siempre mostrar para visibilidad
            print(f"OK {nit} ({asignacion.nombre_proveedor[:40]})")
            print(f"   Facturas: {len(facturas)} | "
                  f"Meses: {analisis['meses_con_facturas']} | "
                  f"CV: {analisis['cv']:.1f}%")
            print(f"   Tipo: {tipo_servicio.value}")
            print(f"   Nivel: {nivel_confianza.value}")
            print(f"   Antigüedad: {analisis['antiguedad_dias']} días")
            print(f"   Monto prom: ${analisis['monto_promedio']:,.0f}")
            print(f"   Requiere OC: {'Sí' if requiere_oc else 'No'}")
            print()

        # Guardar en BD
        if not dry_run:
            asignacion.tipo_servicio_proveedor = tipo_servicio
            asignacion.nivel_confianza_proveedor = nivel_confianza
            asignacion.coeficiente_variacion_historico = Decimal(str(round(analisis['cv'], 2)))
            asignacion.fecha_inicio_relacion = analisis['fecha_primera_factura']
            asignacion.requiere_orden_compra_obligatoria = requiere_oc

            # Metadata de riesgos
            asignacion.metadata_riesgos = {
                'fecha_ultima_clasificacion': datetime.now().isoformat(),
                'facturas_analizadas': len(facturas),
                'meses_con_facturas': analisis['meses_con_facturas'],
                'cv_calculado': round(analisis['cv'], 2),
                'monto_promedio': float(analisis['monto_promedio']),
                'monto_minimo': float(analisis['monto_minimo']),
                'monto_maximo': float(analisis['monto_maximo']),
                'desviacion_estandar': float(analisis['desviacion_estandar']),
                'porcentaje_facturas_con_oc': analisis['porcentaje_con_oc']
            }

            self.db.commit()

        return {
            'clasificado': True,
            'tipo_servicio': tipo_servicio,
            'nivel_confianza': nivel_confianza,
            'cv': analisis['cv'],
            'requiere_oc': requiere_oc
        }

    def _analizar_facturas(self, facturas: List[Factura]) -> Dict[str, any]:
        """Analiza estadísticas de las facturas."""
        montos = [float(f.total_a_pagar) for f in facturas if f.total_a_pagar]

        if not montos:
            return {
                'cv': 999.0,
                'monto_promedio': 0,
                'monto_minimo': 0,
                'monto_maximo': 0,
                'desviacion_estandar': 0,
                'antiguedad_dias': 0,
                'meses_con_facturas': 0,
                'fecha_primera_factura': None,
                'porcentaje_con_oc': 0
            }

        monto_promedio = mean(montos)
        desviacion = stdev(montos) if len(montos) > 1 else 0
        cv = (desviacion / monto_promedio * 100) if monto_promedio > 0 else 0

        # Calcular antigüedad
        fechas = [f.fecha_emision for f in facturas if f.fecha_emision]
        if fechas:
            fecha_primera = min(fechas)
            # Convertir a datetime si es date
            if hasattr(fecha_primera, 'date') and callable(fecha_primera.date):
                # Es un datetime
                antiguedad_dias = (datetime.now() - fecha_primera).days
            else:
                # Es un date, convertir a datetime
                fecha_primera_dt = datetime.combine(fecha_primera, datetime.min.time())
                antiguedad_dias = (datetime.now() - fecha_primera_dt).days
        else:
            fecha_primera = datetime.now()
            antiguedad_dias = 0

        # Calcular meses con facturas
        meses_unicos = set()
        for f in facturas:
            if f.fecha_emision:
                meses_unicos.add(f"{f.fecha_emision.year}-{f.fecha_emision.month:02d}")

        # Porcentaje con orden de compra
        con_oc = sum(1 for f in facturas if f.orden_compra_numero)
        porcentaje_con_oc = (con_oc / len(facturas) * 100) if facturas else 0

        # Convertir fecha_primera a date si es datetime
        if hasattr(fecha_primera, 'date') and callable(fecha_primera.date):
            fecha_primera_date = fecha_primera.date()
        else:
            fecha_primera_date = fecha_primera

        return {
            'cv': cv,
            'monto_promedio': monto_promedio,
            'monto_minimo': min(montos),
            'monto_maximo': max(montos),
            'desviacion_estandar': desviacion,
            'antiguedad_dias': antiguedad_dias,
            'meses_con_facturas': len(meses_unicos),
            'fecha_primera_factura': fecha_primera_date,
            'porcentaje_con_oc': porcentaje_con_oc
        }

    def _determinar_tipo_servicio(self, cv: float) -> TipoServicioProveedor:
        """Determina tipo de servicio según CV."""
        if cv < self.UMBRALES_CV['fijo']:
            return TipoServicioProveedor.SERVICIO_FIJO_MENSUAL
        elif cv < self.UMBRALES_CV['variable']:
            return TipoServicioProveedor.SERVICIO_VARIABLE_PREDECIBLE
        else:
            return TipoServicioProveedor.SERVICIO_POR_CONSUMO

    def _determinar_nivel_confianza(
        self,
        antiguedad_dias: int,
        tipo_servicio: TipoServicioProveedor,
        cv: float
    ) -> NivelConfianzaProveedor:
        """Determina nivel de confianza según antigüedad y tipo."""

        # Proveedores muy nuevos
        if antiguedad_dias < self.UMBRALES_ANTIGUEDAD['bajo']:
            return NivelConfianzaProveedor.NIVEL_5_NUEVO

        # Proveedores de 3-6 meses
        if antiguedad_dias < self.UMBRALES_ANTIGUEDAD['medio']:
            return NivelConfianzaProveedor.NIVEL_4_BAJO

        # Proveedores de 6-12 meses
        if antiguedad_dias < self.UMBRALES_ANTIGUEDAD['alto']:
            return NivelConfianzaProveedor.NIVEL_3_MEDIO

        # Proveedores de 12-24 meses
        if antiguedad_dias < self.UMBRALES_ANTIGUEDAD['critico']:
            # Si es servicio fijo con bajo CV, puede ser nivel 2
            if tipo_servicio == TipoServicioProveedor.SERVICIO_FIJO_MENSUAL and cv < 10:
                return NivelConfianzaProveedor.NIVEL_2_ALTO
            return NivelConfianzaProveedor.NIVEL_3_MEDIO

        # Proveedores 24+ meses
        # Los más antiguos y estables pueden ser nivel 1
        if tipo_servicio == TipoServicioProveedor.SERVICIO_FIJO_MENSUAL and cv < 5:
            return NivelConfianzaProveedor.NIVEL_1_CRITICO

        return NivelConfianzaProveedor.NIVEL_2_ALTO

    def _requiere_orden_compra_obligatoria(
        self,
        tipo_servicio: TipoServicioProveedor,
        cv: float,
        monto_promedio: float
    ) -> bool:
        """Determina si requiere orden de compra obligatoria."""

        # Servicios eventuales siempre requieren OC
        if tipo_servicio == TipoServicioProveedor.SERVICIO_EVENTUAL:
            return True

        # Servicios por consumo requieren OC
        if tipo_servicio == TipoServicioProveedor.SERVICIO_POR_CONSUMO:
            return True

        # Montos altos requieren OC (>$10M COP)
        if monto_promedio > 10_000_000:
            return True

        return False


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Clasificación Enterprise de Proveedores'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Muestra clasificación sin guardar en BD'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Muestra análisis detallado'
    )
    parser.add_argument(
        '--nit',
        type=str,
        help='Clasificar solo un NIT específico'
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        clasificador = ClasificadorProveedoresEnterprise(db, verbose=args.verbose)

        if args.nit:
            # Clasificar un solo NIT
            resultado = clasificador.clasificar_proveedor(args.nit, args.dry_run)
            print(f"\nResultado: {resultado}")
        else:
            # Clasificar todos
            resultados = clasificador.clasificar_todos_proveedores(args.dry_run)

        print("\nClasificación completada exitosamente")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
