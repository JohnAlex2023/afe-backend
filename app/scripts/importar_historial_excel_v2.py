"""
Script de importación adaptado al formato CSV de presupuesto TI 2025.

Este script está adaptado al formato específico del Excel donde:
- Columna "Presupuesto TI ($ mm)" contiene los nombres de cuenta
- Columna "Responsable" contiene el responsable
- Columnas " Ej Ene-25 " ... " Ej Dic-25 " contienen los montos ejecutados
- Columna "Facturas" contiene referencias a facturas

Autor: Sistema de Automatización AFE
Fecha: 2025-10-08
"""

import sys
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal
from collections import defaultdict
import statistics

import pandas as pd
from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.session import SessionLocal
from app.models.historial_pagos import HistorialPagos, TipoPatron
from app.models.proveedor import Proveedor


class ImportadorHistorialExcelV2:
    """Importador adaptado al formato específico del CSV de presupuesto TI."""

    # Umbrales de clasificación
    UMBRAL_TIPO_A = 5.0
    UMBRAL_TIPO_B = 30.0

    def __init__(self, db: Session):
        self.db = db
        self.stats = {
            'lineas_procesadas': 0,
            'patrones_creados': 0,
            'patrones_actualizados': 0,
            'errores': 0,
            'proveedores_nuevos': 0
        }
        self.errores_detalle = []

    def importar_desde_csv(self, file_path: str, año_analisis: int = 2025) -> Dict[str, Any]:
        """Importa historial desde CSV con formato específico."""
        print("="*80)
        print("IMPORTACION DE HISTORIAL - FORMATO PRESUPUESTO TI")
        print("="*80)
        print(f"Archivo: {file_path}")
        print(f"Año: {año_analisis}")
        print()

        try:
            # Leer CSV con header en fila 6
            df = pd.read_csv(file_path, encoding='utf-8-sig', header=6)
            print(f"PASO 1: Archivo cargado - {len(df)} filas")

            # Extraer datos
            datos = self._extraer_datos(df)
            print(f"PASO 2: {len(datos)} líneas con datos válidos extraídas")

            if not datos:
                print("\nADVERTENCIA: No se encontraron datos válidos en el CSV")
                print("Verifica que el archivo tenga:")
                print("  - Columna 'Presupuesto TI ($ mm)' con nombres de cuenta")
                print("  - Columnas ' Ej Ene-25 ' ... ' Ej Dic-25 ' con montos")
                return {'exito': False, 'mensaje': 'Sin datos válidos'}

            # Agrupar por patrón
            grupos = self._agrupar_por_patron(datos)
            print(f"PASO 3: {len(grupos)} patrones únicos detectados")

            # Calcular estadísticas
            patrones = self._calcular_estadisticas(grupos, año_analisis)
            print(f"PASO 4: Estadísticas calculadas para {len(patrones)} patrones")

            # Persistir
            self._persistir_patrones(patrones)
            print(f"PASO 5: Guardado en BD")
            print(f"  - Creados: {self.stats['patrones_creados']}")
            print(f"  - Actualizados: {self.stats['patrones_actualizados']}")

            # Resumen
            resumen = self._generar_resumen(patrones)
            self._imprimir_resumen(resumen)

            print()
            print("="*80)
            print("IMPORTACION COMPLETADA EXITOSAMENTE")
            print("="*80)

            return {
                'exito': True,
                'estadisticas': self.stats,
                'resumen': resumen
            }

        except Exception as e:
            print(f"\nERROR CRITICO: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'exito': False, 'error': str(e)}

    def _extraer_datos(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extrae datos del DataFrame."""
        datos = []

        # Columnas de montos ejecutados
        cols_ejecucion = [
            " Ej Ene-25 ", " Ej Feb-25 ", " Ej Mar-25 ", " Ej Abr-25 ",
            " Ej May-25 ", " Ej Jun-25 ", " Ej Jul-25 ", " Ej Ago-25 ",
            " Ej Sep-25 ", " Ej Oct-25 ", " Ej Nov-25 ", " Ej Dic-25 "
        ]

        for idx, row in df.iterrows():
            try:
                # Obtener nombre de cuenta (en columna "Presupuesto TI ($ mm)")
                concepto = row.get("Presupuesto TI ($ mm)")
                if pd.isna(concepto) or not str(concepto).strip():
                    continue

                concepto = str(concepto).strip()

                # Saltar filas de agrupación (como "Sistemas de Información")
                if len(concepto) < 10 or concepto.startswith("Sistemas de"):
                    continue

                # Obtener responsable
                responsable = row.get("Responsable")
                if pd.notna(responsable):
                    responsable = str(responsable).strip()
                else:
                    responsable = None

                # Extraer montos mensuales
                montos = []
                meses = []
                for mes_idx, col in enumerate(cols_ejecucion, start=1):
                    if col in row.index:
                        monto = self._parse_monto(row[col])
                        if monto > 0:
                            montos.append(float(monto))
                            meses.append(mes_idx)

                # Solo procesar si tiene al menos 2 pagos
                if len(montos) >= 2:
                    # Normalizar concepto y extraer proveedor
                    concepto_norm, proveedor = self._normalizar_concepto(concepto)

                    datos.append({
                        'concepto_original': concepto,
                        'concepto_normalizado': concepto_norm,
                        'proveedor_nombre': proveedor or responsable or "DESCONOCIDO",
                        'responsable': responsable,
                        'montos': montos,
                        'meses': meses,
                        'cantidad_pagos': len(montos)
                    })

                    self.stats['lineas_procesadas'] += 1

            except Exception as e:
                self.errores_detalle.append({'fila': idx, 'error': str(e)})
                self.stats['errores'] += 1

        return datos

    def _parse_monto(self, valor: Any) -> Decimal:
        """Parsea un monto del CSV."""
        if pd.isna(valor):
            return Decimal('0')

        try:
            # Convertir a string y limpiar
            valor_str = str(valor).strip()
            valor_str = valor_str.replace(',', '').replace(' ', '').replace('$', '')
            valor_str = valor_str.replace('(', '').replace(')', '')

            # Manejar casos especiales
            if not valor_str or valor_str == '-' or valor_str == 'nan':
                return Decimal('0')

            return Decimal(valor_str)
        except:
            return Decimal('0')

    def _normalizar_concepto(self, concepto: str) -> tuple:
        """Normaliza concepto y extrae proveedor."""
        proveedor = None

        # Buscar proveedor en formato "... - PROVEEDOR"
        if ' - ' in concepto:
            partes = concepto.split(' - ')
            if len(partes) >= 2:
                concepto_base = partes[0].strip()
                proveedor = partes[-1].strip().upper()
            else:
                concepto_base = concepto
        else:
            concepto_base = concepto

        # Normalizar
        norm = concepto_base.lower().strip()
        norm = norm.replace('á', 'a').replace('é', 'e').replace('í', 'i')
        norm = norm.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
        norm = norm[:200]

        return norm, proveedor

    def _agrupar_por_patron(self, datos: List[Dict]) -> Dict:
        """Agrupa por proveedor + concepto."""
        grupos = defaultdict(list)

        for item in datos:
            key = f"{item['proveedor_nombre']}|{item['concepto_normalizado']}"
            grupos[key].append(item)

        return dict(grupos)

    def _calcular_estadisticas(self, grupos: Dict, año: int) -> List[Dict]:
        """Calcula estadísticas por patrón."""
        patrones = []

        for key, items in grupos.items():
            try:
                proveedor_nombre, concepto_norm = key.split('|', 1)

                # Consolidar montos
                todos_montos = []
                meses_unicos = set()
                for item in items:
                    todos_montos.extend(item['montos'])
                    meses_unicos.update(item['meses'])

                if len(todos_montos) < 2:
                    continue

                # Estadísticas
                promedio = Decimal(str(statistics.mean(todos_montos)))
                minimo = Decimal(str(min(todos_montos)))
                maximo = Decimal(str(max(todos_montos)))
                desv_std = Decimal(str(statistics.stdev(todos_montos)))

                # Coeficiente de variación
                cv = (desv_std / promedio * 100) if promedio > 0 else Decimal('0')

                # Clasificar
                if cv < self.UMBRAL_TIPO_A:
                    tipo = TipoPatron.TIPO_A
                elif cv < self.UMBRAL_TIPO_B:
                    tipo = TipoPatron.TIPO_B
                else:
                    tipo = TipoPatron.TIPO_C

                # Auto-aprobar
                puede_auto = tipo in [TipoPatron.TIPO_A, TipoPatron.TIPO_B] and len(todos_montos) >= 3

                # Rangos para TIPO_B
                rango_inf = max(Decimal('0'), promedio - (2 * desv_std)) if tipo == TipoPatron.TIPO_B else None
                rango_sup = promedio + (2 * desv_std) if tipo == TipoPatron.TIPO_B else None

                # Hash
                concepto_hash = hashlib.md5(concepto_norm.encode('utf-8')).hexdigest()

                patrones.append({
                    'proveedor_nombre': proveedor_nombre,
                    'concepto_normalizado': concepto_norm,
                    'concepto_hash': concepto_hash,
                    'tipo_patron': tipo,
                    'pagos_analizados': len(todos_montos),
                    'meses_con_pagos': len(meses_unicos),
                    'monto_promedio': promedio,
                    'monto_minimo': minimo,
                    'monto_maximo': maximo,
                    'desviacion_estandar': desv_std,
                    'coeficiente_variacion': cv,
                    'rango_inferior': rango_inf,
                    'rango_superior': rango_sup,
                    'puede_aprobar_auto': 1 if puede_auto else 0,
                    'umbral_alerta': Decimal('15.0') if tipo == TipoPatron.TIPO_A else Decimal('30.0')
                })

            except Exception as e:
                self.errores_detalle.append({'patron': key, 'error': str(e)})
                self.stats['errores'] += 1

        return patrones

    def _persistir_patrones(self, patrones: List[Dict]):
        """Guarda patrones en BD."""
        for patron in patrones:
            try:
                # Obtener o crear proveedor
                proveedor = self._get_or_create_proveedor(patron['proveedor_nombre'])
                if not proveedor:
                    continue

                # Buscar patrón existente
                existente = self.db.query(HistorialPagos).filter(
                    HistorialPagos.proveedor_id == proveedor.id,
                    HistorialPagos.concepto_hash == patron['concepto_hash']
                ).first()

                if existente:
                    # Actualizar
                    for key in ['tipo_patron', 'pagos_analizados', 'meses_con_pagos',
                               'monto_promedio', 'monto_minimo', 'monto_maximo',
                               'desviacion_estandar', 'coeficiente_variacion',
                               'rango_inferior', 'rango_superior', 'puede_aprobar_auto', 'umbral_alerta']:
                        setattr(existente, key, patron[key])
                    existente.fecha_analisis = datetime.utcnow()
                    self.stats['patrones_actualizados'] += 1
                else:
                    # Crear
                    nuevo = HistorialPagos(
                        proveedor_id=proveedor.id,
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
                        puede_aprobar_auto=patron['puede_aprobar_auto'],
                        umbral_alerta=patron['umbral_alerta'],
                        fecha_analisis=datetime.utcnow(),
                        version_algoritmo="2.0"
                    )
                    self.db.add(nuevo)
                    self.stats['patrones_creados'] += 1

                if (self.stats['patrones_creados'] + self.stats['patrones_actualizados']) % 10 == 0:
                    self.db.commit()

            except Exception as e:
                self.db.rollback()
                self.errores_detalle.append({'patron': patron['concepto_normalizado'], 'error': str(e)})
                self.stats['errores'] += 1

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"ERROR en commit final: {str(e)}")

    def _get_or_create_proveedor(self, nombre: str) -> Optional[Proveedor]:
        """Obtiene o crea proveedor."""
        # Buscar
        proveedor = self.db.query(Proveedor).filter(
            Proveedor.razon_social.ilike(f"%{nombre}%")
        ).first()

        if proveedor:
            return proveedor

        # Crear
        try:
            nit_temp = f"TEMP-{hashlib.md5(nombre.encode()).hexdigest()[:10].upper()}"
            nuevo = Proveedor(
                nit=nit_temp,
                razon_social=nombre,
                area="TI",
                activo=True
            )
            self.db.add(nuevo)
            self.db.commit()
            self.db.refresh(nuevo)
            self.stats['proveedores_nuevos'] += 1
            return nuevo
        except:
            self.db.rollback()
            return None

    def _generar_resumen(self, patrones: List[Dict]) -> Dict:
        """Genera resumen."""
        tipo_a = sum(1 for p in patrones if p['tipo_patron'] == TipoPatron.TIPO_A)
        tipo_b = sum(1 for p in patrones if p['tipo_patron'] == TipoPatron.TIPO_B)
        tipo_c = sum(1 for p in patrones if p['tipo_patron'] == TipoPatron.TIPO_C)
        auto = sum(1 for p in patrones if p['puede_aprobar_auto'] == 1)

        return {
            'total': len(patrones),
            'tipo_a': tipo_a,
            'tipo_b': tipo_b,
            'tipo_c': tipo_c,
            'auto_aprobables': auto,
            'porcentaje': (auto / len(patrones) * 100) if patrones else 0
        }

    def _imprimir_resumen(self, resumen: Dict):
        """Imprime resumen."""
        print(f"\nPASO 6: RESUMEN")
        print(f"  Total patrones: {resumen['total']}")
        print(f"  - TIPO_A (Fijo, CV<5%): {resumen['tipo_a']}")
        print(f"  - TIPO_B (Fluctuante, CV<30%): {resumen['tipo_b']}")
        print(f"  - TIPO_C (Excepcional, CV>30%): {resumen['tipo_c']}")
        print(f"  Auto-aprobables: {resumen['auto_aprobables']} ({resumen['porcentaje']:.1f}%)")
        print(f"\n  Proveedores nuevos: {self.stats['proveedores_nuevos']}")
        print(f"  Errores: {self.stats['errores']}")


def main():
    """Función principal."""
    archivo = r"C:\Users\jhont\PRIVADO_ODO\AVD PPTO TI 2025 - Presentación JZ - OPEX y Menor Cuantia(TI DSZF).csv"

    if not Path(archivo).exists():
        print(f"ERROR: Archivo no encontrado: {archivo}")
        return 1

    db = SessionLocal()

    try:
        importador = ImportadorHistorialExcelV2(db)
        resultado = importador.importar_desde_csv(archivo, año_analisis=2025)
        return 0 if resultado['exito'] else 1
    except Exception as e:
        print(f"ERROR FATAL: {str(e)}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
