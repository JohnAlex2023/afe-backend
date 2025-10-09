"""
Script ONE-TIME de importación de historial de facturas desde Excel a historial_pagos.

Este script bootstrap inicial:
1. Lee el CSV con facturas pagadas del año 2025
2. Agrupa por proveedor + concepto normalizado
3. Calcula estadísticas (promedio, desviación, CV)
4. Clasifica en TIPO_A (fijo), TIPO_B (fluctuante), TIPO_C (excepcional)
5. Inserta en tabla historial_pagos para alimentar el motor de automatización

Uso:
    python -m app.scripts.importar_historial_excel

Nivel: Enterprise Fortune 500
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

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.session import SessionLocal
from app.models.historial_pagos import HistorialPagos, TipoPatron
from app.models.proveedor import Proveedor
from app.crud import proveedor as crud_proveedor


class ImportadorHistorialExcel:
    """
    Importador profesional de historial de facturas desde Excel.

    Características enterprise:
    - Validación de datos robusta
    - Normalización de conceptos
    - Cálculo estadístico preciso
    - Clasificación automática de patrones
    - Logging detallado para auditoría
    - Manejo de errores granular
    """

    # Mapeo de columnas del CSV (con espacios)
    COLUMNA_NOMBRE_CUENTA = "NOMB CTA"
    COLUMNA_RESPONSABLE = "Responsable"
    COLUMNA_FACTURAS = "Facturas"
    COLUMNAS_EJECUCION = [
        " Ej Ene-25 ", " Ej Feb-25 ", " Ej Mar-25 ", " Ej Abr-25 ",
        " Ej May-25 ", " Ej Jun-25 ", " Ej Jul-25 ", " Ej Ago-25 ",
        " Ej Sep-25 ", " Ej Oct-25 ", " Ej Nov-25 ", " Ej Dic-25 "
    ]

    # Umbrales de clasificación de patrones (según documento)
    UMBRAL_TIPO_A = 5.0   # CV < 5% = Valor fijo
    UMBRAL_TIPO_B = 30.0  # CV < 30% = Valor fluctuante predecible
    # CV > 30% = TIPO_C (excepcional)

    def __init__(self, db: Session):
        """
        Inicializa el importador.

        Args:
            db: Sesión de base de datos SQLAlchemy
        """
        self.db = db
        self.stats = {
            'lineas_procesadas': 0,
            'patrones_creados': 0,
            'patrones_actualizados': 0,
            'errores': 0,
            'proveedores_nuevos': 0,
            'proveedores_encontrados': 0
        }
        self.errores_detalle = []

    def importar_desde_csv(
        self,
        file_path: str,
        año_analisis: int = 2025,
        solo_ultimos_meses: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Importa historial de facturas desde CSV.

        Args:
            file_path: Ruta al archivo CSV
            año_analisis: Año fiscal del análisis (default: 2025)
            solo_ultimos_meses: Si se especifica, solo analiza los últimos N meses

        Returns:
            Diccionario con estadísticas de la importación
        """
        print("="*80)
        print("IMPORTACIÓN DE HISTORIAL DE FACTURAS - BOOTSTRAP INICIAL")
        print("="*80)
        print(f"Archivo: {file_path}")
        print(f"Año fiscal: {año_analisis}")
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        try:
            # 1. Leer CSV
            print(" PASO 1: Cargando archivo CSV...")
            df = self._leer_csv(file_path)
            print(f"    {len(df)} filas cargadas")
            print()

            # 2. Extraer y validar datos
            print("🔍 PASO 2: Extrayendo datos de facturas...")
            datos_facturas = self._extraer_datos_facturas(df, solo_ultimos_meses)
            print(f"    {len(datos_facturas)} líneas de gasto extraídas")
            print()

            # 3. Agrupar por proveedor + concepto
            print(" PASO 3: Agrupando por proveedor y concepto...")
            grupos_patrones = self._agrupar_por_patron(datos_facturas)
            print(f"    {len(grupos_patrones)} patrones únicos detectados")
            print()

            # 4. Calcular estadísticas y clasificar
            print("PASO 4: Calculando estadísticas y clasificando patrones...")
            patrones_calculados = self._calcular_estadisticas_patrones(grupos_patrones, año_analisis)
            print(f"   Estadísticas calculadas para {len(patrones_calculados)} patrones")
            print()

            # 5. Persistir en base de datos
            print("PASO 5: Guardando en base de datos...")
            self._persistir_patrones(patrones_calculados)
            print(f"   Creados: {self.stats['patrones_creados']}")
            print(f"   Actualizados: {self.stats['patrones_actualizados']}")
            print()

            # 6. Generar resumen
            print("PASO 6: Generando resumen...")
            resumen = self._generar_resumen(patrones_calculados)
            self._imprimir_resumen(resumen)

            print()
            print("="*80)
            print("IMPORTACIÓN COMPLETADA EXITOSAMENTE")
            print("="*80)

            return {
                'exito': True,
                'estadisticas': self.stats,
                'resumen': resumen,
                'errores': self.errores_detalle
            }

        except Exception as e:
            print(f"\nERROR CRÍTICO: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'exito': False,
                'error': str(e),
                'estadisticas': self.stats,
                'errores': self.errores_detalle
            }

    def _leer_csv(self, file_path: str) -> pd.DataFrame:
        """Lee y valida el archivo CSV."""
        try:
            df = pd.read_csv(
                file_path,
                encoding='utf-8-sig',
                header=6,  # La fila 7 (índice 6) contiene los encabezados
                na_values=['', 'NA', 'N/A', '-', 'nan'],
                keep_default_na=True
            )

            # Validar que existan las columnas requeridas
            columnas_requeridas = [self.COLUMNA_NOMBRE_CUENTA, self.COLUMNA_RESPONSABLE]
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]

            if columnas_faltantes:
                raise ValueError(f"Columnas faltantes en CSV: {', '.join(columnas_faltantes)}")

            return df

        except Exception as e:
            raise Exception(f"Error al leer CSV: {str(e)}")

    def _extraer_datos_facturas(
        self,
        df: pd.DataFrame,
        solo_ultimos_meses: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Extrae y estructura los datos de facturas del DataFrame.
        """
        datos_facturas = []

        # Determinar qué columnas de ejecución usar
        columnas_ejecucion = self.COLUMNAS_EJECUCION
        if solo_ultimos_meses:
            columnas_ejecucion = columnas_ejecucion[:solo_ultimos_meses]

        for idx, row in df.iterrows():
            # Ya no necesitamos saltar filas porque skiprows=6 ya lo hizo
            try:
                # Extraer datos básicos
                concepto = self._extraer_valor_string(row, self.COLUMNA_NOMBRE_CUENTA)
                responsable = self._extraer_valor_string(row, self.COLUMNA_RESPONSABLE)
                facturas_str = self._extraer_valor_string(row, self.COLUMNA_FACTURAS)

                # Saltar si no tiene concepto
                if not concepto:
                    continue

                # Extraer montos mensuales
                montos_mensuales = []
                meses_con_datos = []

                for mes_idx, col_nombre in enumerate(columnas_ejecucion, start=1):
                    if col_nombre in row.index:
                        monto = self._extraer_valor_numerico(row, col_nombre)
                        if monto > 0:
                            montos_mensuales.append(float(monto))
                            meses_con_datos.append(mes_idx)

                # Solo procesar si tiene al menos 2 pagos
                if len(montos_mensuales) >= 2:
                    # Normalizar concepto y extraer proveedor
                    concepto_normalizado, proveedor_nombre = self._normalizar_concepto(concepto)

                    datos_facturas.append({
                        'concepto_original': concepto,
                        'concepto_normalizado': concepto_normalizado,
                        'proveedor_nombre': proveedor_nombre or responsable or "PROVEEDOR DESCONOCIDO",
                        'responsable': responsable,
                        'montos': montos_mensuales,
                        'meses': meses_con_datos,
                        'facturas_raw': facturas_str,
                        'cantidad_pagos': len(montos_mensuales)
                    })

                    self.stats['lineas_procesadas'] += 1

            except Exception as e:
                self.errores_detalle.append({
                    'fila': idx,
                    'error': str(e)
                })
                self.stats['errores'] += 1

        return datos_facturas

    def _extraer_valor_string(self, row: pd.Series, columna: str) -> Optional[str]:
        """Extrae valor string de una columna, manejando NaN."""
        if columna not in row.index:
            return None
        valor = row[columna]
        if pd.isna(valor):
            return None
        return str(valor).strip()

    def _extraer_valor_numerico(self, row: pd.Series, columna: str) -> Decimal:
        """Extrae valor numérico de una columna y lo convierte a Decimal."""
        if columna not in row.index:
            return Decimal('0')

        valor = row[columna]
        if pd.isna(valor):
            return Decimal('0')

        try:
            # Limpiar valor (quitar símbolos)
            if isinstance(valor, str):
                valor = valor.replace('$', '').replace(',', '').replace(' ', '').strip()

            return Decimal(str(valor))
        except:
            return Decimal('0')

    def _normalizar_concepto(self, concepto: str) -> tuple[str, Optional[str]]:
        """
        Normaliza el concepto y extrae el nombre del proveedor si está presente.

        Args:
            concepto: Concepto original (ej: "Historia Clinica - GOMEDISYS")

        Returns:
            Tupla (concepto_normalizado, proveedor_nombre)
        """
        # Extraer proveedor si está en formato "Concepto - PROVEEDOR"
        proveedor_nombre = None
        if ' - ' in concepto:
            partes = concepto.split(' - ')
            if len(partes) >= 2:
                concepto_base = partes[0].strip()
                proveedor_nombre = partes[-1].strip().upper()
            else:
                concepto_base = concepto
        else:
            concepto_base = concepto

        # Normalizar: minúsculas, sin acentos, sin caracteres especiales
        concepto_normalizado = concepto_base.lower().strip()
        concepto_normalizado = concepto_normalizado.replace('á', 'a').replace('é', 'e').replace('í', 'i')
        concepto_normalizado = concepto_normalizado.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')

        # Limitar longitud
        if len(concepto_normalizado) > 200:
            concepto_normalizado = concepto_normalizado[:200]

        return concepto_normalizado, proveedor_nombre

    def _agrupar_por_patron(self, datos_facturas: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Agrupa las facturas por proveedor + concepto normalizado.

        Returns:
            Diccionario {key: [facturas]} donde key = "proveedor|concepto_normalizado"
        """
        grupos = defaultdict(list)

        for factura in datos_facturas:
            # Crear clave única: proveedor + concepto
            key = f"{factura['proveedor_nombre']}|{factura['concepto_normalizado']}"
            grupos[key].append(factura)

        return dict(grupos)

    def _calcular_estadisticas_patrones(
        self,
        grupos_patrones: Dict[str, List[Dict[str, Any]]],
        año_analisis: int
    ) -> List[Dict[str, Any]]:
        """
        Calcula estadísticas detalladas para cada patrón detectado.
        """
        patrones_calculados = []

        for key, facturas_grupo in grupos_patrones.items():
            try:
                proveedor_nombre, concepto_normalizado = key.split('|', 1)

                # Consolidar todos los montos del grupo
                todos_montos = []
                meses_unicos = set()

                for factura in facturas_grupo:
                    todos_montos.extend(factura['montos'])
                    meses_unicos.update(factura['meses'])

                # Calcular estadísticas
                if len(todos_montos) < 2:
                    continue

                monto_promedio = Decimal(str(statistics.mean(todos_montos)))
                monto_minimo = Decimal(str(min(todos_montos)))
                monto_maximo = Decimal(str(max(todos_montos)))
                desviacion_std = Decimal(str(statistics.stdev(todos_montos))) if len(todos_montos) > 1 else Decimal('0')

                # Coeficiente de variación (CV%)
                cv = (desviacion_std / monto_promedio * 100) if monto_promedio > 0 else Decimal('0')

                # Clasificar tipo de patrón según CV
                if cv < self.UMBRAL_TIPO_A:
                    tipo_patron = TipoPatron.TIPO_A
                elif cv < self.UMBRAL_TIPO_B:
                    tipo_patron = TipoPatron.TIPO_B
                else:
                    tipo_patron = TipoPatron.TIPO_C

                # Determinar si puede aprobar automáticamente
                # Solo TIPO_A y TIPO_B con suficiente historial
                puede_aprobar_auto = (
                    tipo_patron in [TipoPatron.TIPO_A, TipoPatron.TIPO_B] and
                    len(todos_montos) >= 3
                )

                # Calcular rangos para TIPO_B
                rango_inferior = None
                rango_superior = None
                if tipo_patron == TipoPatron.TIPO_B:
                    rango_inferior = max(Decimal('0'), monto_promedio - (2 * desviacion_std))
                    rango_superior = monto_promedio + (2 * desviacion_std)

                # Calcular umbral de alerta (20% de desviación para TIPO_A, 30% para TIPO_B)
                umbral_alerta = Decimal('20.0') if tipo_patron == TipoPatron.TIPO_A else Decimal('30.0')

                # Generar hash del concepto
                concepto_hash = hashlib.md5(concepto_normalizado.encode('utf-8')).hexdigest()

                # Construir diccionario de patrón
                patron = {
                    'proveedor_nombre': proveedor_nombre,
                    'concepto_normalizado': concepto_normalizado,
                    'concepto_hash': concepto_hash,
                    'tipo_patron': tipo_patron,
                    'pagos_analizados': len(todos_montos),
                    'meses_con_pagos': len(meses_unicos),
                    'monto_promedio': monto_promedio,
                    'monto_minimo': monto_minimo,
                    'monto_maximo': monto_maximo,
                    'desviacion_estandar': desviacion_std,
                    'coeficiente_variacion': cv,
                    'rango_inferior': rango_inferior,
                    'rango_superior': rango_superior,
                    'puede_aprobar_auto': 1 if puede_aprobar_auto else 0,
                    'umbral_alerta': umbral_alerta,
                    'facturas_detalle': facturas_grupo,
                    'año_analisis': año_analisis
                }

                patrones_calculados.append(patron)

            except Exception as e:
                self.errores_detalle.append({
                    'patron_key': key,
                    'error': f"Error calculando estadísticas: {str(e)}"
                })
                self.stats['errores'] += 1

        return patrones_calculados

    def _persistir_patrones(self, patrones: List[Dict[str, Any]]) -> None:
        """
        Persiste los patrones calculados en la tabla historial_pagos.
        """
        for patron in patrones:
            try:
                # 1. Obtener o crear proveedor
                proveedor = self._obtener_o_crear_proveedor(patron['proveedor_nombre'])

                if not proveedor:
                    self.errores_detalle.append({
                        'patron': patron['concepto_normalizado'],
                        'error': 'No se pudo crear/obtener proveedor'
                    })
                    self.stats['errores'] += 1
                    continue

                # 2. Verificar si ya existe el patrón
                patron_existente = self.db.query(HistorialPagos).filter(
                    HistorialPagos.proveedor_id == proveedor.id,
                    HistorialPagos.concepto_hash == patron['concepto_hash']
                ).first()

                if patron_existente:
                    # Actualizar patrón existente
                    self._actualizar_patron_existente(patron_existente, patron)
                    self.stats['patrones_actualizados'] += 1
                else:
                    # Crear nuevo patrón
                    self._crear_nuevo_patron(proveedor.id, patron)
                    self.stats['patrones_creados'] += 1

                # Commit cada 10 patrones para evitar transacciones muy largas
                if (self.stats['patrones_creados'] + self.stats['patrones_actualizados']) % 10 == 0:
                    self.db.commit()

            except Exception as e:
                self.db.rollback()
                self.errores_detalle.append({
                    'patron': patron['concepto_normalizado'],
                    'error': f"Error persistiendo: {str(e)}"
                })
                self.stats['errores'] += 1

        # Commit final
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error en commit final: {str(e)}")

    def _obtener_o_crear_proveedor(self, proveedor_nombre: str) -> Optional[Proveedor]:
        """
        Busca proveedor por nombre o lo crea si no existe.
        """
        # Buscar por razon_social (case-insensitive)
        proveedor = self.db.query(Proveedor).filter(
            Proveedor.razon_social.ilike(f"%{proveedor_nombre}%")
        ).first()

        if proveedor:
            self.stats['proveedores_encontrados'] += 1
            return proveedor

        # Crear nuevo proveedor
        try:
            # Generar NIT temporal basado en hash del nombre
            nit_temp = f"TEMP-{hashlib.md5(proveedor_nombre.encode()).hexdigest()[:10].upper()}"

            nuevo_proveedor = Proveedor(
                nit=nit_temp,
                razon_social=proveedor_nombre,
                area="TI",  # Asumiendo que es TI por el contexto del Excel
                activo=True
            )

            self.db.add(nuevo_proveedor)
            self.db.commit()
            self.db.refresh(nuevo_proveedor)

            self.stats['proveedores_nuevos'] += 1
            return nuevo_proveedor

        except Exception as e:
            self.db.rollback()
            print(f"   ⚠️  Error creando proveedor {proveedor_nombre}: {str(e)}")
            return None

    def _crear_nuevo_patron(self, proveedor_id: int, patron: Dict[str, Any]) -> None:
        """Crea un nuevo registro en historial_pagos."""
        nuevo_historial = HistorialPagos(
            proveedor_id=proveedor_id,
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
            version_algoritmo="1.0"
        )

        self.db.add(nuevo_historial)

    def _actualizar_patron_existente(self, patron_existente: HistorialPagos, patron_nuevo: Dict[str, Any]) -> None:
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
        patron_existente.puede_aprobar_auto = patron_nuevo['puede_aprobar_auto']
        patron_existente.umbral_alerta = patron_nuevo['umbral_alerta']
        patron_existente.fecha_analisis = datetime.utcnow()

    def _generar_resumen(self, patrones: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Genera resumen estadístico de los patrones."""
        tipo_a = sum(1 for p in patrones if p['tipo_patron'] == TipoPatron.TIPO_A)
        tipo_b = sum(1 for p in patrones if p['tipo_patron'] == TipoPatron.TIPO_B)
        tipo_c = sum(1 for p in patrones if p['tipo_patron'] == TipoPatron.TIPO_C)

        auto_aprobables = sum(1 for p in patrones if p['puede_aprobar_auto'] == 1)

        return {
            'total_patrones': len(patrones),
            'tipo_a_fijo': tipo_a,
            'tipo_b_fluctuante': tipo_b,
            'tipo_c_excepcional': tipo_c,
            'auto_aprobables': auto_aprobables,
            'porcentaje_automatizable': (auto_aprobables / len(patrones) * 100) if patrones else 0
        }

    def _imprimir_resumen(self, resumen: Dict[str, Any]) -> None:
        """Imprime resumen formateado."""
        print(f"   Total patrones detectados: {resumen['total_patrones']}")
        print(f"   └─ TIPO_A (Fijo, CV<5%): {resumen['tipo_a_fijo']}")
        print(f"   └─ TIPO_B (Fluctuante, CV<30%): {resumen['tipo_b_fluctuante']}")
        print(f"   └─ TIPO_C (Excepcional, CV>30%): {resumen['tipo_c_excepcional']}")
        print()
        print(f"    Patrones auto-aprobables: {resumen['auto_aprobables']} ({resumen['porcentaje_automatizable']:.1f}%)")
        print()
        print(f"    Estadísticas globales:")
        print(f"      - Proveedores nuevos creados: {self.stats['proveedores_nuevos']}")
        print(f"      - Proveedores encontrados: {self.stats['proveedores_encontrados']}")
        print(f"      - Errores: {self.stats['errores']}")


def main():
    """
    Función principal de ejecución del script.
    """
    # Configuración
    ARCHIVO_CSV = r"C:\Users\jhont\PRIVADO_ODO\AVD PPTO TI 2025 - Presentación JZ - OPEX y Menor Cuantia(TI DSZF).csv"
    AÑO_ANALISIS = 2025
    SOLO_ULTIMOS_MESES = None  # None = todos los meses, 3 = solo últimos 3 meses

    # Validar que existe el archivo
    if not Path(ARCHIVO_CSV).exists():
        print(f" ERROR: No se encontró el archivo: {ARCHIVO_CSV}")
        print()
        print("Por favor, ajusta la ruta ARCHIVO_CSV en el script.")
        return

    # Crear sesión de BD
    db = SessionLocal()

    try:
        # Ejecutar importación
        importador = ImportadorHistorialExcel(db)
        resultado = importador.importar_desde_csv(
            file_path=ARCHIVO_CSV,
            año_analisis=AÑO_ANALISIS,
            solo_ultimos_meses=SOLO_ULTIMOS_MESES
        )

        # Mostrar errores si los hay
        if resultado['errores']:
            print()
            print("  ERRORES DETECTADOS:")
            print("-"*80)
            for error in resultado['errores'][:10]:  # Mostrar primeros 10
                print(f"   {error}")
            if len(resultado['errores']) > 10:
                print(f"   ... y {len(resultado['errores']) - 10} errores más")

        # Retornar código de salida
        return 0 if resultado['exito'] else 1

    except Exception as e:
        print(f"\n ERROR FATAL: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
