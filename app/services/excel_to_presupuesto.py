"""
Servicio de importación de archivos Excel de presupuesto a la tabla lineas_presupuesto.

Transforma datos de Excel al modelo enterprise de control presupuestal.

Nivel: Enterprise Fortune 500
"""
import pandas as pd
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app.crud import presupuesto as crud_presupuesto
from app.models.presupuesto import LineaPresupuesto


class ExcelPresupuestoImporter:
    """
    Importador de archivos Excel de presupuesto al sistema enterprise.

    Características:
    - Parsea Excel/CSV con estructura de presupuesto mensual
    - Crea líneas presupuestales en la base de datos
    - Valida datos y genera reportes de importación
    - Maneja errores y provee feedback detallado
    """

    # Mapeo de nombres de mes a abreviatura
    MESES_NOMBRES = {
        'enero': 'ene', 'febrero': 'feb', 'marzo': 'mar', 'abril': 'abr',
        'mayo': 'may', 'junio': 'jun', 'julio': 'jul', 'agosto': 'ago',
        'septiembre': 'sep', 'octubre': 'oct', 'noviembre': 'nov', 'diciembre': 'dic',
        'ene': 'ene', 'feb': 'feb', 'mar': 'mar', 'abr': 'abr',
        'may': 'may', 'jun': 'jun', 'jul': 'jul', 'ago': 'ago',
        'sep': 'sep', 'oct': 'oct', 'nov': 'nov', 'dic': 'dic',
        'jan': 'ene', 'feb': 'feb', 'mar': 'mar', 'apr': 'abr',
        'may': 'may', 'jun': 'jun', 'jul': 'jul', 'aug': 'ago',
        'sep': 'sep', 'oct': 'oct', 'nov': 'nov', 'dec': 'dic'
    }

    def __init__(self, db: Session):
        """
        Inicializa el importador.

        Args:
            db: Sesión de base de datos
        """
        self.db = db
        self.df = None
        self.errores = []
        self.advertencias = []

    def importar_desde_excel(
        self,
        file_path: str,
        año_fiscal: int,
        responsable_id: int,
        categoria: str = "TI",
        creado_por: str = "ADMIN",
        hoja: str | int = 0,
        fila_inicio: int = 0,
        mapeo_columnas: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Importa datos de presupuesto desde un archivo Excel.

        Args:
            file_path: Ruta al archivo Excel/CSV
            año_fiscal: Año fiscal del presupuesto
            responsable_id: ID del responsable por defecto
            categoria: Categoría del presupuesto (TI, Operaciones, etc.)
            creado_por: Usuario que realiza la importación
            hoja: Nombre o índice de la hoja a leer (para Excel)
            fila_inicio: Fila donde empiezan los datos (0-indexed)
            mapeo_columnas: Configuración de mapeo de columnas

        Returns:
            Dict con estadísticas de importación
        """
        self.errores = []
        self.advertencias = []

        # Configuración por defecto de mapeo de columnas
        if mapeo_columnas is None:
            mapeo_columnas = {
                "codigo": "ID",  # Columna que contiene el código de la línea
                "nombre": "Nombre cuenta",  # Columna con el nombre
                "descripcion": "Descripción",
                "centro_costo": "Centro de Costo",
                "subcategoria": "Subcategoría",
                "proveedor_preferido": "Proveedor",
                # Presupuestos mensuales
                "presupuesto_ene": "Ene-25",
                "presupuesto_feb": "Feb-25",
                "presupuesto_mar": "Mar-25",
                "presupuesto_abr": "Abr-25",
                "presupuesto_may": "May-25",
                "presupuesto_jun": "Jun-25",
                "presupuesto_jul": "Jul-25",
                "presupuesto_ago": "Ago-25",
                "presupuesto_sep": "Sep-25",
                "presupuesto_oct": "Oct-25",
                "presupuesto_nov": "Nov-25",
                "presupuesto_dic": "Dic-25",
            }

        # Leer archivo
        try:
            if file_path.endswith('.csv'):
                self.df = pd.read_csv(
                    file_path,
                    encoding='utf-8-sig',
                    skiprows=fila_inicio
                )
            else:
                self.df = pd.read_excel(
                    file_path,
                    sheet_name=hoja,
                    skiprows=fila_inicio
                )
        except Exception as e:
            return {
                "exito": False,
                "error": f"Error al leer archivo: {str(e)}",
                "lineas_importadas": 0
            }

        # Validar que existan columnas mínimas requeridas
        columnas_requeridas = ["codigo", "nombre"]
        for col in columnas_requeridas:
            if col not in mapeo_columnas or mapeo_columnas[col] not in self.df.columns:
                return {
                    "exito": False,
                    "error": f"Columna requerida '{col}' ({mapeo_columnas.get(col)}) no encontrada",
                    "columnas_disponibles": list(self.df.columns)
                }

        # Procesar filas
        lineas_creadas = []
        lineas_actualizadas = []

        for idx, row in self.df.iterrows():
            try:
                # Extraer código y nombre
                codigo = self._extraer_valor(row, mapeo_columnas.get("codigo"))
                nombre = self._extraer_valor(row, mapeo_columnas.get("nombre"))

                # Saltar filas sin código o nombre
                if not codigo or not nombre:
                    continue

                # Normalizar código
                codigo = str(codigo).strip()

                # Verificar si ya existe
                linea_existente = crud_presupuesto.get_linea_by_codigo(
                    self.db,
                    codigo=codigo,
                    año_fiscal=año_fiscal
                )

                # Extraer presupuestos mensuales
                presupuestos_mensuales = {}
                for mes in ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]:
                    col_name = mapeo_columnas.get(f"presupuesto_{mes}")
                    if col_name:
                        valor = self._extraer_valor_numerico(row, col_name)
                        presupuestos_mensuales[mes] = valor
                    else:
                        presupuestos_mensuales[mes] = Decimal("0.00")

                # Extraer campos opcionales
                descripcion = self._extraer_valor(row, mapeo_columnas.get("descripcion"))
                centro_costo = self._extraer_valor(row, mapeo_columnas.get("centro_costo"))
                subcategoria = self._extraer_valor(row, mapeo_columnas.get("subcategoria"))
                proveedor_preferido = self._extraer_valor(row, mapeo_columnas.get("proveedor_preferido"))

                if linea_existente:
                    # Actualizar línea existente
                    self.advertencias.append(f"Línea {codigo} ya existe, actualizando...")

                    campos_actualizar = {
                        "nombre": nombre,
                        "descripcion": descripcion,
                        "centro_costo": centro_costo,
                        "subcategoria": subcategoria,
                        "proveedor_preferido": proveedor_preferido,
                    }

                    # Actualizar presupuestos mensuales
                    for mes, valor in presupuestos_mensuales.items():
                        campos_actualizar[f"presupuesto_{mes}"] = valor

                    linea_actualizada = crud_presupuesto.update_linea_presupuesto(
                        db=self.db,
                        linea_id=linea_existente.id,
                        actualizado_por=creado_por,
                        **campos_actualizar
                    )
                    lineas_actualizadas.append(linea_actualizada)

                else:
                    # Crear nueva línea
                    nueva_linea = crud_presupuesto.create_linea_presupuesto(
                        db=self.db,
                        codigo=codigo,
                        nombre=nombre,
                        descripcion=descripcion,
                        responsable_id=responsable_id,
                        año_fiscal=año_fiscal,
                        presupuestos_mensuales=presupuestos_mensuales,
                        centro_costo=centro_costo,
                        categoria=categoria,
                        subcategoria=subcategoria,
                        proveedor_preferido=proveedor_preferido,
                        creado_por=creado_por
                    )
                    lineas_creadas.append(nueva_linea)

            except Exception as e:
                self.errores.append(f"Fila {idx}: {str(e)}")
                continue

        return {
            "exito": True,
            "lineas_creadas": len(lineas_creadas),
            "lineas_actualizadas": len(lineas_actualizadas),
            "total_procesadas": len(lineas_creadas) + len(lineas_actualizadas),
            "errores": self.errores,
            "advertencias": self.advertencias,
            "ids_creados": [linea.id for linea in lineas_creadas],
            "ids_actualizados": [linea.id for linea in lineas_actualizadas]
        }

    def _extraer_valor(self, row: pd.Series, nombre_columna: Optional[str]) -> Optional[str]:
        """Extrae valor de texto de una columna."""
        if not nombre_columna or nombre_columna not in row.index:
            return None

        valor = row[nombre_columna]
        if pd.isna(valor):
            return None

        return str(valor).strip()

    def _extraer_valor_numerico(self, row: pd.Series, nombre_columna: Optional[str]) -> Decimal:
        """Extrae valor numérico de una columna y lo convierte a Decimal."""
        if not nombre_columna or nombre_columna not in row.index:
            return Decimal("0.00")

        valor = row[nombre_columna]
        if pd.isna(valor):
            return Decimal("0.00")

        try:
            # Limpiar valor (quitar símbolos de moneda, comas, etc.)
            if isinstance(valor, str):
                valor = valor.replace('$', '').replace(',', '').replace(' ', '').strip()

            return Decimal(str(valor))
        except:
            return Decimal("0.00")

    def generar_plantilla_excel(
        self,
        output_path: str,
        año_fiscal: int,
        incluir_ejemplo: bool = True
    ):
        """
        Genera una plantilla Excel para importación de presupuesto.

        Args:
            output_path: Ruta donde guardar la plantilla
            año_fiscal: Año fiscal de la plantilla
            incluir_ejemplo: Si True, incluye una fila de ejemplo
        """
        # Crear DataFrame con estructura
        columnas = [
            "ID",
            "Nombre cuenta",
            "Descripción",
            "Centro de Costo",
            "Subcategoría",
            "Proveedor",
            "Ene-25", "Feb-25", "Mar-25", "Abr-25", "May-25", "Jun-25",
            "Jul-25", "Ago-25", "Sep-25", "Oct-25", "Nov-25", "Dic-25"
        ]

        data = []
        if incluir_ejemplo:
            data.append({
                "ID": "TI-001",
                "Nombre cuenta": "Licencias Microsoft 365",
                "Descripción": "Suscripción anual Microsoft 365 Business",
                "Centro de Costo": "CC-TI",
                "Subcategoría": "Software",
                "Proveedor": "Microsoft",
                "Ene-25": 5000000,
                "Feb-25": 5000000,
                "Mar-25": 5000000,
                "Abr-25": 5000000,
                "May-25": 5000000,
                "Jun-25": 5000000,
                "Jul-25": 5000000,
                "Ago-25": 5000000,
                "Sep-25": 5000000,
                "Oct-25": 5000000,
                "Nov-25": 5000000,
                "Dic-25": 5000000,
            })

        df = pd.DataFrame(data, columns=columnas)

        # Guardar
        if output_path.endswith('.csv'):
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
        else:
            df.to_excel(output_path, index=False, sheet_name=f"Presupuesto {año_fiscal}")

        return {
            "exito": True,
            "archivo": output_path,
            "columnas": columnas
        }
