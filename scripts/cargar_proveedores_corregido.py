"""
Script MEJORADO para cargar proveedores desde CSV.

CORRECCIONES:
1. Delimitador CORRECTO: semicolon (;) en lugar de coma
2. Filtrado CORRECTO de NITs inválidos (valor "0")
3. Carga COMPLETA de todos los proveedores únicos
4. Reporte detallado de operaciones

USO:
    python scripts/cargar_proveedores_corregido.py \
        --csv-path "path/to/Listas Terceros(Hoja1).csv"
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, List, Tuple

# Agregar path para importar modelos
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.proveedor import Proveedor
from sqlalchemy import func
from app.utils.logger import logger


class CargadorProveedoresCSVMejorado:
    """
    Cargador profesional de proveedores desde CSV con delimitador CORRECTO.
    """

    def __init__(self, csv_path: str, dry_run: bool = False):
        self.csv_path = Path(csv_path)
        self.dry_run = dry_run
        self.db = SessionLocal()

        # Estadísticas
        self.total_filas = 0
        self.nits_unicos_totales = 0
        self.nits_invalidos = 0
        self.proveedores_actualizados = 0
        self.proveedores_nuevos = 0
        self.proveedores_reactivados = 0
        self.detalles_operacion = []

    def validar_csv(self) -> bool:
        """Valida que el archivo CSV exista y sea legible."""
        print(f"\n[1] Validando archivo CSV...")

        if not self.csv_path.exists():
            print(f"   ERROR: Archivo no encontrado: {self.csv_path}")
            return False

        if not self.csv_path.is_file():
            print(f"   ERROR: No es un archivo: {self.csv_path}")
            return False

        print(f"   OK: Archivo encontrado: {self.csv_path}")
        return True

    def leer_csv(self) -> Dict[str, Dict]:
        """
        Lee CSV con delimitador SEMICOLON (;).

        Retorna diccionario:
        {
            'nit': {
                'razon_social': nombre,
                'sedes': [lista de SEDE],
                'emails': [lista de CUENTA única]
            }
        }
        """
        print(f"\n[2] Leyendo archivo CSV con delimitador SEMICOLON...")

        proveedores = {}

        try:
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                # IMPORTANTE: delimiter=';' (semicolon, no coma)
                reader = csv.DictReader(f, delimiter=';')

                for row_num, row in enumerate(reader, start=2):  # start=2 para saltar encabezado
                    self.total_filas += 1

                    nit = row.get('NIT', '').strip()
                    tercero = row.get('Tercero', '').strip()
                    sede = row.get('SEDE', '').strip()
                    cuenta = row.get('CUENTA', '').strip()

                    # FILTRADO: Excluir NITs inválidos
                    if not nit or nit == '0' or nit == '':
                        self.nits_invalidos += 1
                        self.detalles_operacion.append(
                            f"Fila {row_num}: NIT inválido ('{nit}') para {tercero}"
                        )
                        continue

                    # Primer NIT único
                    if nit not in proveedores:
                        self.nits_unicos_totales += 1
                        proveedores[nit] = {
                            'razon_social': tercero,
                            'sedes': set(),
                            'emails': set()
                        }

                    # Agregar SEDE si existe
                    if sede:
                        proveedores[nit]['sedes'].add(sede)

                    # Agregar EMAIL si existe
                    if cuenta:
                        proveedores[nit]['emails'].add(cuenta)

        except Exception as e:
            print(f"   ERROR al leer CSV: {str(e)}")
            return {}

        print(f"   OK: Leído correctamente")
        print(f"      - Total de filas: {self.total_filas}")
        print(f"      - NITs únicos válidos encontrados: {self.nits_unicos_totales}")
        print(f"      - NITs inválidos (0 o vacíos): {self.nits_invalidos}")

        return proveedores

    def obtener_proveedores_existentes(self) -> Dict[str, Proveedor]:
        """Obtiene proveedores ya en BD para comparar."""
        print(f"\n[3] Consultando proveedores existentes en BD...")

        existentes = {}
        try:
            todos = self.db.query(Proveedor).all()
            for proveedor in todos:
                existentes[proveedor.nit] = proveedor

            print(f"   OK: {len(existentes)} proveedores ya en BD")
        except Exception as e:
            print(f"   ERROR: {str(e)}")

        return existentes

    def procesar_proveedores(
        self,
        proveedores_csv: Dict,
        existentes_bd: Dict
    ) -> Tuple[List[Proveedor], List[Proveedor], List[Proveedor]]:
        """
        Procesa proveedores para insertar/actualizar.

        Retorna:
            (nuevos, a_actualizar, reactivados)
        """
        print(f"\n[4] Procesando proveedores...")

        nuevos = []
        a_actualizar = []
        reactivados = []

        for nit, datos_csv in proveedores_csv.items():
            razon_social = datos_csv['razon_social']
            # Usar primer SEDE o None
            area = list(datos_csv['sedes'])[0] if datos_csv['sedes'] else None
            # Usar primer email o None
            contacto_email = list(datos_csv['emails'])[0] if datos_csv['emails'] else None

            if nit in existentes_bd:
                # ACTUALIZAR existente
                proveedor = existentes_bd[nit]

                # Actualizar campos si son mejores/más completos
                if razon_social and len(razon_social) > len(proveedor.razon_social or ''):
                    proveedor.razon_social = razon_social

                if area and not proveedor.area:
                    proveedor.area = area

                if contacto_email and not proveedor.contacto_email:
                    proveedor.contacto_email = contacto_email

                a_actualizar.append(proveedor)
                self.detalles_operacion.append(
                    f"Actualizar: {nit} - {razon_social}"
                )
            else:
                # CREAR nuevo
                proveedor = Proveedor(
                    nit=nit,
                    razon_social=razon_social,
                    area=area,
                    contacto_email=contacto_email,
                    activo=True
                )
                nuevos.append(proveedor)
                self.detalles_operacion.append(
                    f"Nuevo: {nit} - {razon_social}"
                )

        print(f"   OK: Proveedores procesados")
        print(f"      - Nuevos a insertar: {len(nuevos)}")
        print(f"      - Existentes a actualizar: {len(a_actualizar)}")

        return nuevos, a_actualizar, reactivados

    def ejecutar(self) -> bool:
        """Ejecuta el proceso completo de carga."""
        print("\n" + "="*70)
        print("CARGADOR MEJORADO DE PROVEEDORES DESDE CSV")
        print("="*70)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Modo: {'DRY RUN (sin cambios)' if self.dry_run else 'PRODUCCION'}")

        try:
            # Paso 1: Validar CSV
            if not self.validar_csv():
                return False

            # Paso 2: Leer CSV
            proveedores_csv = self.leer_csv()
            if not proveedores_csv:
                print("ERROR: No se pudieron leer proveedores del CSV")
                return False

            # Paso 3: Obtener existentes
            existentes_bd = self.obtener_proveedores_existentes()

            # Paso 4: Procesar
            nuevos, a_actualizar, reactivados = self.procesar_proveedores(
                proveedores_csv,
                existentes_bd
            )

            # Paso 5: Aplicar cambios
            print(f"\n[5] Aplicando cambios a BD...")

            if not self.dry_run:
                try:
                    # Actualizar existentes
                    for proveedor in a_actualizar:
                        self.db.add(proveedor)

                    # Insertar nuevos
                    for proveedor in nuevos:
                        self.db.add(proveedor)

                    # Commit atómico
                    self.db.commit()

                    self.proveedores_nuevos = len(nuevos)
                    self.proveedores_actualizados = len(a_actualizar)

                    print(f"   OK: Cambios aplicados exitosamente")
                except Exception as e:
                    self.db.rollback()
                    print(f"   ERROR en transacción: {str(e)}")
                    return False
            else:
                print(f"   DRY RUN: No se aplicaron cambios (modo simulación)")
                self.proveedores_nuevos = len(nuevos)
                self.proveedores_actualizados = len(a_actualizar)

            # Paso 6: Generar reporte
            self.generar_reporte()

            return True

        except Exception as e:
            print(f"\nERROR CRÍTICO: {str(e)}")
            return False
        finally:
            self.db.close()

    def generar_reporte(self):
        """Genera reporte final de operaciones."""
        print("\n" + "="*70)
        print("REPORTE FINAL")
        print("="*70)

        print(f"\nOPERACIONES REALIZADAS:")
        print(f"  - Nuevos proveedores insertados: {self.proveedores_nuevos}")
        print(f"  - Proveedores existentes actualizados: {self.proveedores_actualizados}")
        print(f"  - Proveedores reactivados: {self.proveedores_reactivados}")

        print(f"\nANÁLISIS DEL ARCHIVO CSV:")
        print(f"  - Total de filas: {self.total_filas}")
        print(f"  - NITs únicos válidos: {self.nits_unicos_totales}")
        print(f"  - NITs inválidos (0 o vacíos): {self.nits_invalidos}")

        # Total en BD
        total_bd = self.db.query(func.count(Proveedor.id)).scalar()
        print(f"\nESTADO DE LA BD:")
        print(f"  - Total de proveedores en BD: {total_bd}")

        print("\n" + "="*70)
        print("CARGA COMPLETADA EXITOSAMENTE")
        print("="*70 + "\n")


def main():
    """Punto de entrada del script."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Cargador mejorado de proveedores desde CSV'
    )
    parser.add_argument(
        '--csv-path',
        required=True,
        help='Ruta del archivo CSV'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Modo simulación (sin cambios en BD)'
    )

    args = parser.parse_args()

    # Crear cargador
    cargador = CargadorProveedoresCSVMejorado(
        csv_path=args.csv_path,
        dry_run=args.dry_run
    )

    # Ejecutar
    success = cargador.ejecutar()

    # Retornar código de salida
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
