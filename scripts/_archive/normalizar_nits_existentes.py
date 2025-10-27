"""
Script para normalizar NITs existentes en la base de datos.

Este script corrige NITs con formatos inconsistentes:
- "890903938-4" -> "890903938"
- "890.903.938-4" -> "890903938"
- "890.903.938" -> "890903938"

USO:
    # Modo dry-run (recomendado primero)
    python scripts/normalizar_nits_existentes.py --dry-run

    # Modo producción
    python scripts/normalizar_nits_existentes.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Agregar path para importar modelos
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.proveedor import Proveedor
from app.utils.normalizacion import normalizar_nit


class NormalizadorNITs:
    """Normaliza NITs existentes en la base de datos."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.db = SessionLocal()
        self.total_proveedores = 0
        self.nits_normalizados = 0
        self.sin_cambios = 0
        self.cambios = []

    def ejecutar(self) -> bool:
        """Ejecuta el proceso de normalización."""
        print("\n" + "="*70)
        print("NORMALIZADOR DE NITs - Base de Datos de Proveedores")
        print("="*70)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Modo: {'DRY RUN (sin cambios)' if self.dry_run else 'PRODUCCION'}")
        print()

        try:
            # Obtener todos los proveedores
            print("[1] Consultando proveedores...")
            proveedores = self.db.query(Proveedor).all()
            self.total_proveedores = len(proveedores)
            print(f"   OK: {self.total_proveedores} proveedores encontrados")

            # Normalizar NITs
            print("\n[2] Normalizando NITs...")
            for proveedor in proveedores:
                nit_original = proveedor.nit
                nit_normalizado = normalizar_nit(nit_original)

                if nit_normalizado and nit_normalizado != nit_original:
                    # NIT necesita normalización
                    self.nits_normalizados += 1
                    self.cambios.append({
                        'id': proveedor.id,
                        'razon_social': proveedor.razon_social,
                        'nit_original': nit_original,
                        'nit_normalizado': nit_normalizado
                    })

                    if not self.dry_run:
                        proveedor.nit = nit_normalizado
                else:
                    self.sin_cambios += 1

            # Aplicar cambios
            if not self.dry_run and self.nits_normalizados > 0:
                print(f"\n[3] Aplicando cambios a BD...")
                self.db.commit()
                print(f"   OK: Cambios aplicados exitosamente")
            else:
                print(f"\n[3] {'DRY RUN: Sin cambios aplicados' if self.dry_run else 'No hay cambios para aplicar'}")

            # Generar reporte
            self.generar_reporte()

            return True

        except Exception as e:
            print(f"\nERROR CRÍTICO: {str(e)}")
            if not self.dry_run:
                self.db.rollback()
            return False
        finally:
            self.db.close()

    def generar_reporte(self):
        """Genera reporte final de operaciones."""
        print("\n" + "="*70)
        print("REPORTE FINAL")
        print("="*70)

        print(f"\nESTADÍSTICAS:")
        print(f"  - Total proveedores: {self.total_proveedores}")
        print(f"  - NITs normalizados: {self.nits_normalizados}")
        print(f"  - NITs sin cambios: {self.sin_cambios}")

        if self.cambios:
            print(f"\nCAMBIOS REALIZADOS:")
            print("-" * 70)
            for cambio in self.cambios[:20]:  # Mostrar primeros 20
                print(f"  ID {cambio['id']}: {cambio['razon_social']}")
                print(f"    ANTES: {cambio['nit_original']}")
                print(f"    DESPUÉS: {cambio['nit_normalizado']}")
                print()

            if len(self.cambios) > 20:
                print(f"  ... y {len(self.cambios) - 20} más")

        print("\n" + "="*70)
        if self.dry_run:
            print("DRY RUN COMPLETADO - No se aplicaron cambios")
        else:
            print("NORMALIZACIÓN COMPLETADA EXITOSAMENTE")
        print("="*70 + "\n")


def main():
    """Punto de entrada del script."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Normaliza NITs existentes en la base de datos'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Modo simulación (sin cambios en BD)'
    )

    args = parser.parse_args()

    # Crear normalizador
    normalizador = NormalizadorNITs(dry_run=args.dry_run)

    # Ejecutar
    success = normalizador.ejecutar()

    # Retornar código de salida
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
