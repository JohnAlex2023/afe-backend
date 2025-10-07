"""
Servicio empresarial de importación y comparación de facturas desde Excel/CSV.

Funcionalidades:
1. Parsear archivo Excel/CSV de presupuesto TI
2. Extraer valores presupuestados vs ejecutados por mes
3. Comparar con facturas reales en BD
4. Generar reporte de desviaciones
5. Identificar facturas faltantes o duplicadas

Autor: Backend AFE
Fecha: 2025-10-04
"""

import pandas as pd
import re
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from pathlib import Path


class ExcelFacturaImporter:
    """
    Importador profesional de facturas desde Excel de presupuesto.
    """

    # Mapeo de meses en español a número
    MESES_MAP = {
        'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    def __init__(self, file_path: str):
        """
        Inicializa el importador con la ruta del archivo.

        Args:
            file_path: Ruta completa al archivo CSV/Excel
        """
        self.file_path = Path(file_path)
        self.df = None
        self.data_cleaned = []

    def parse_file(self) -> pd.DataFrame:
        """
        Parse el archivo Excel/CSV y retorna DataFrame limpio.

        Returns:
            DataFrame con datos procesados
        """
        try:
            # Leer CSV con encoding UTF-8
            self.df = pd.read_csv(
                self.file_path,
                encoding='utf-8-sig',  # Maneja BOM
                na_values=['', 'NA', 'N/A', '-'],
                keep_default_na=True
            )

            print(f"✅ Archivo cargado: {len(self.df)} filas")
            return self.df

        except Exception as e:
            print(f"❌ Error al cargar archivo: {str(e)}")
            raise

    def extract_presupuesto_data(self) -> List[Dict[str, Any]]:
        """
        Extrae datos de presupuesto y ejecución por línea de gasto.

        Returns:
            Lista de diccionarios con datos por línea presupuestal
        """
        if self.df is None:
            self.parse_file()

        extracted_data = []

        # Empezar desde fila 7 (header) y 8 (datos)
        # Columnas importantes:
        # 1: ID
        # 4: Nombre cuenta
        # 8: Responsable
        # 11-22: Presupuesto mensual (Jan-25 a Dec-25)
        # 23-34: Ejecución mensual (Ej Ene-25 a Ej Dic-25)
        # 37: Facturas

        for idx, row in self.df.iterrows():
            # Saltar filas de encabezado y vacías
            if idx < 7:
                continue

            # Obtener valores básicos
            id_linea = row.iloc[1] if pd.notna(row.iloc[1]) else None
            nombre_cuenta = row.iloc[4] if pd.notna(row.iloc[4]) else None
            responsable = row.iloc[8] if pd.notna(row.iloc[8]) else None

            # Saltar si no tiene ID o nombre
            if not id_linea or not nombre_cuenta:
                continue

            # Extraer presupuesto mensual (columnas 11-22)
            presupuesto_mensual = {}
            for mes_idx, mes_num in enumerate(range(1, 13), start=11):
                valor = self._parse_currency(row.iloc[mes_idx])
                mes_nombre = self._get_mes_nombre(mes_num)
                presupuesto_mensual[mes_nombre] = valor

            # Extraer ejecución mensual (columnas 23-34)
            ejecucion_mensual = {}
            for mes_idx, mes_num in enumerate(range(1, 13), start=23):
                valor = self._parse_currency(row.iloc[mes_idx])
                mes_nombre = self._get_mes_nombre(mes_num)
                ejecucion_mensual[mes_nombre] = valor

            # Extraer números de factura (columna 37)
            facturas_str = row.iloc[37] if pd.notna(row.iloc[37]) else ""
            facturas = self._extract_facturas(facturas_str)

            # Construir registro
            linea_data = {
                'id_linea': int(id_linea),
                'nombre_cuenta': nombre_cuenta.strip(),
                'responsable': responsable.strip() if responsable else None,
                'presupuesto_mensual': presupuesto_mensual,
                'ejecucion_mensual': ejecucion_mensual,
                'facturas': facturas,
                'total_presupuesto_anual': sum(presupuesto_mensual.values()),
                'total_ejecucion_anual': sum(ejecucion_mensual.values()),
                'desviacion_anual': sum(ejecucion_mensual.values()) - sum(presupuesto_mensual.values())
            }

            extracted_data.append(linea_data)

        self.data_cleaned = extracted_data
        print(f"✅ Extraídas {len(extracted_data)} líneas presupuestales")
        return extracted_data

    def _parse_currency(self, value: Any) -> Decimal:
        """
        Convierte valor de moneda en string a Decimal.

        Args:
            value: Valor en formato string o numérico

        Returns:
            Decimal con el valor limpio
        """
        if pd.isna(value) or value is None:
            return Decimal('0')

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        # Limpiar string: quitar espacios, comas, puntos de miles
        value_str = str(value).strip()
        value_str = value_str.replace(',', '')  # Quitar comas
        value_str = value_str.replace(' ', '')  # Quitar espacios
        value_str = value_str.replace('$', '')  # Quitar símbolo $

        try:
            return Decimal(value_str)
        except:
            return Decimal('0')

    def _get_mes_nombre(self, mes_num: int) -> str:
        """
        Retorna nombre corto del mes.

        Args:
            mes_num: Número de mes (1-12)

        Returns:
            Nombre de mes en español (ene, feb, mar...)
        """
        meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
                 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
        return meses[mes_num - 1]

    def _extract_facturas(self, facturas_str: str) -> List[str]:
        """
        Extrae números de factura del campo de texto.

        Busca patrones como:
        - KION - Ene -821
        - DISR93354
        - E896

        Args:
            facturas_str: String con números de factura

        Returns:
            Lista de números de factura encontrados
        """
        if not facturas_str or pd.isna(facturas_str):
            return []

        # Buscar patrones de número de factura
        # Patrón 1: "KION - Ene -821" -> extraer "821"
        # Patrón 2: "DISR93354" -> completo
        # Patrón 3: "E896" -> completo

        facturas = []

        # Buscar patrón: Proveedor - Mes - Número
        pattern1 = r'([A-Z]+)\s*-\s*([A-Za-z]{3})\s*-?\s*(\d+)'
        matches1 = re.findall(pattern1, facturas_str)
        for match in matches1:
            proveedor, mes, numero = match
            # Construir número de factura
            factura_num = f"{proveedor.upper()}-{mes.title()}-{numero}"
            facturas.append(factura_num)

        # Buscar patrón: Alfanumérico directo (DISR93354, E896)
        pattern2 = r'\b([A-Z]+\d+)\b'
        matches2 = re.findall(pattern2, facturas_str)
        facturas.extend(matches2)

        return list(set(facturas))  # Eliminar duplicados

    def compare_with_db(self, db_facturas: List[Dict]) -> Dict[str, Any]:
        """
        Compara datos del Excel con facturas reales de la base de datos.

        Args:
            db_facturas: Lista de facturas desde la BD con formato:
                [{
                    'numero_factura': 'FACT-001',
                    'total': 1500.00,
                    'fecha_emision': '2025-01-15',
                    'periodo_factura': '2025-01',
                    'proveedor': 'KION'
                }]

        Returns:
            Dict con reporte de comparación:
            {
                'total_lineas_excel': 50,
                'total_facturas_db': 100,
                'facturas_encontradas': [...],
                'facturas_faltantes': [...],
                'desviaciones_presupuesto': [...]
            }
        """
        if not self.data_cleaned:
            self.extract_presupuesto_data()

        # Crear mapa de facturas BD por número
        db_map = {f['numero_factura']: f for f in db_facturas}

        encontradas = []
        faltantes = []
        desviaciones = []

        for linea in self.data_cleaned:
            for factura_num in linea['facturas']:
                if factura_num in db_map:
                    factura_db = db_map[factura_num]
                    encontradas.append({
                        'numero_factura': factura_num,
                        'linea_presupuestal': linea['nombre_cuenta'],
                        'total_bd': factura_db['total'],
                        'periodo': factura_db['periodo_factura']
                    })
                else:
                    faltantes.append({
                        'numero_factura': factura_num,
                        'linea_presupuestal': linea['nombre_cuenta'],
                        'responsable': linea['responsable']
                    })

            # Calcular desviaciones por línea
            for mes, valor_presupuesto in linea['presupuesto_mensual'].items():
                valor_ejecucion = linea['ejecucion_mensual'][mes]
                desviacion = valor_ejecucion - valor_presupuesto

                if abs(desviacion) > 100:  # Solo reportar desviaciones > $100
                    desviaciones.append({
                        'linea': linea['nombre_cuenta'],
                        'mes': mes,
                        'presupuesto': float(valor_presupuesto),
                        'ejecucion': float(valor_ejecucion),
                        'desviacion': float(desviacion),
                        'porcentaje': (float(desviacion) / float(valor_presupuesto) * 100) if valor_presupuesto > 0 else 0
                    })

        return {
            'total_lineas_excel': len(self.data_cleaned),
            'total_facturas_db': len(db_facturas),
            'facturas_encontradas': encontradas,
            'facturas_faltantes': faltantes,
            'desviaciones_presupuesto': sorted(desviaciones, key=lambda x: abs(x['desviacion']), reverse=True),
            'resumen': {
                'total_presupuesto_anual': sum(l['total_presupuesto_anual'] for l in self.data_cleaned),
                'total_ejecucion_anual': sum(l['total_ejecucion_anual'] for l in self.data_cleaned),
                'desviacion_global': sum(l['desviacion_anual'] for l in self.data_cleaned)
            }
        }

    def generate_report(self, comparison: Dict) -> str:
        """
        Genera reporte textual de comparación.

        Args:
            comparison: Resultado de compare_with_db()

        Returns:
            String con reporte formateado
        """
        report = []
        report.append("="*80)
        report.append("REPORTE DE COMPARACIÓN: PRESUPUESTO vs EJECUCIÓN")
        report.append("="*80)
        report.append(f"\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Resumen general
        report.append(" RESUMEN GENERAL")
        report.append("-"*80)
        report.append(f"Líneas presupuestales: {comparison['total_lineas_excel']}")
        report.append(f"Facturas en BD: {comparison['total_facturas_db']}")
        report.append(f"Facturas encontradas: {len(comparison['facturas_encontradas'])}")
        report.append(f"Facturas faltantes: {len(comparison['facturas_faltantes'])}\n")

        # Resumen financiero
        resumen = comparison['resumen']
        report.append("💰 RESUMEN FINANCIERO")
        report.append("-"*80)
        report.append(f"Presupuesto anual total: ${resumen['total_presupuesto_anual']:,.2f}")
        report.append(f"Ejecución anual total: ${resumen['total_ejecucion_anual']:,.2f}")
        report.append(f"Desviación global: ${resumen['desviacion_global']:,.2f}\n")

        # Facturas faltantes
        if comparison['facturas_faltantes']:
            report.append(" FACTURAS FALTANTES EN BD")
            report.append("-"*80)
            for f in comparison['facturas_faltantes'][:10]:  # Top 10
                report.append(f"  - {f['numero_factura']:<20} | {f['linea_presupuestal']}")
            if len(comparison['facturas_faltantes']) > 10:
                report.append(f"  ... y {len(comparison['facturas_faltantes']) - 10} más\n")

        # Desviaciones mayores
        if comparison['desviaciones_presupuesto']:
            report.append(" TOP 10 DESVIACIONES PRESUPUESTALES")
            report.append("-"*80)
            for d in comparison['desviaciones_presupuesto'][:10]:
                report.append(f"  {d['linea'][:40]:<40} | {d['mes']:<5} | ${d['desviacion']:>15,.2f} ({d['porcentaje']:>6.1f}%)")

        report.append("="*80)
        return "\n".join(report)


# Ejemplo de uso
if __name__ == "__main__":
    file_path = r"c:\Users\jhont\Downloads\AVD PPTO TI 2025 - Presentación JZ - OPEX y Menor Cuantia - Copia(TI DSZF).csv"

    importer = ExcelFacturaImporter(file_path)
    data = importer.extract_presupuesto_data()

    print(f"\n Procesadas {len(data)} líneas")
    print(f"\nEjemplo de primera línea:")
    if data:
        linea = data[0]
        print(f"  Nombre: {linea['nombre_cuenta']}")
        print(f"  Responsable: {linea['responsable']}")
        print(f"  Facturas: {linea['facturas']}")
        print(f"  Presupuesto anual: ${linea['total_presupuesto_anual']:,.2f}")
        print(f"  Ejecución anual: ${linea['total_ejecucion_anual']:,.2f}")
