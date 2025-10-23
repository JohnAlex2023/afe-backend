"""
Script para fusionar proveedores duplicados ANTES de normalizar NITs.

ORDEN CORRECTO:
1. PRIMERO: Fusionar duplicados (este script)
2. DESPUÉS: Normalizar NITs (normalizar_nits_existentes.py)

Este script:
- Detecta proveedores que tendrían el mismo NIT después de normalizar
- Fusiona manteniendo el registro más completo
- Actualiza referencias (facturas, asignaciones)
- Elimina duplicados

USO:
    python scripts/fusionar_duplicados_proveedores.py --dry-run
    python scripts/fusionar_duplicados_proveedores.py
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.proveedor import Proveedor
from app.models.factura import Factura
from app.utils.normalizacion import normalizar_nit
from sqlalchemy import func, text


class FusionadorDuplicados:
    """Fusiona proveedores que serían duplicados después de normalizar."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.db = SessionLocal()
        self.grupos_duplicados = []
        self.registros_eliminados = 0
        self.facturas_actualizadas = 0
        self.asignaciones_actualizadas = 0

    def detectar_duplicados(self) -> List[Dict]:
        """Detecta grupos de proveedores con el mismo NIT normalizado."""
        print("\n[1] Detectando duplicados (simulando normalización)...")

        todos = self.db.query(Proveedor).all()

        # Agrupar por NIT normalizado
        grupos: Dict[str, List[Proveedor]] = {}
        for p in todos:
            nit_norm = normalizar_nit(p.nit)
            if not nit_norm:
                continue

            if nit_norm not in grupos:
                grupos[nit_norm] = []
            grupos[nit_norm].append(p)

        # Filtrar grupos con duplicados
        duplicados = []
        for nit_norm, proveedores in grupos.items():
            if len(proveedores) > 1:
                duplicados.append({
                    'nit_normalizado': nit_norm,
                    'proveedores': proveedores,
                    'cantidad': len(proveedores)
                })

        print(f"   Grupos duplicados encontrados: {len(duplicados)}")
        return duplicados

    def seleccionar_mejor_registro(self, proveedores: List[Proveedor]) -> Proveedor:
        """
        Selecciona el mejor registro de un grupo.

        Prioridad:
        1. Tiene más información (área, email)
        2. NIT más corto (sin DV)
        3. ID más bajo (más antiguo)
        """
        def score(p: Proveedor) -> tuple:
            return (
                1 if p.area else 0,
                1 if p.contacto_email else 0,
                -len(p.nit or ''),  # Más corto primero
                -p.id  # Más antiguo primero
            )

        return max(proveedores, key=score)

    def fusionar_grupo(self, grupo: Dict) -> Dict:
        """Fusiona un grupo de duplicados."""
        proveedores = grupo['proveedores']
        mejor = self.seleccionar_mejor_registro(proveedores)
        duplicados = [p for p in proveedores if p.id != mejor.id]

        resultado = {
            'nit_normalizado': grupo['nit_normalizado'],
            'mantener': mejor,
            'eliminar': duplicados,
            'facturas_actualizadas': 0,
            'asignaciones_actualizadas': 0
        }

        # Actualizar referencias
        for dup in duplicados:
            # Facturas
            facturas = self.db.query(Factura).filter(
                Factura.proveedor_id == dup.id
            ).all()

            for f in facturas:
                f.proveedor_id = mejor.id
                resultado['facturas_actualizadas'] += 1

            # Historial pagos
            try:
                result_hp = self.db.execute(
                    text("UPDATE historial_pagos SET proveedor_id = :nuevo WHERE proveedor_id = :viejo"),
                    {'nuevo': mejor.id, 'viejo': dup.id}
                )
            except Exception:
                pass

            # Asignaciones
            try:
                nit_norm = normalizar_nit(mejor.nit)
                result = self.db.execute(
                    text("UPDATE asignacion_nit_responsable SET nit = :nit_nuevo WHERE nit = :nit_viejo"),
                    {'nit_nuevo': nit_norm, 'nit_viejo': dup.nit}
                )
                resultado['asignaciones_actualizadas'] += result.rowcount
            except Exception:
                pass

        return resultado

    def ejecutar(self) -> bool:
        """Ejecuta fusión de duplicados."""
        print("\n" + "="*70)
        print("FUSIONADOR DE PROVEEDORES DUPLICADOS")
        print("="*70)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Modo: {'DRY RUN (sin cambios)' if self.dry_run else 'PRODUCCION'}")

        try:
            # Detectar
            duplicados = self.detectar_duplicados()

            if not duplicados:
                print("\n  No se encontraron duplicados")
                return True

            # Procesar
            print(f"\n[2] Procesando {len(duplicados)} grupos...")
            print("-" * 70)

            for grupo in duplicados:
                resultado = self.fusionar_grupo(grupo)

                mejor = resultado['mantener']
                eliminar = resultado['eliminar']

                print(f"\nNIT Normalizado: {grupo['nit_normalizado']}")
                print(f"  MANTENER -> ID {mejor.id}: {mejor.nit:15s} | {mejor.razon_social[:40]:40s}")
                print(f"              Area: {(mejor.area or 'N/A')[:15]:15s} | Email: {('Si' if mejor.contacto_email else 'No'):3s}")

                for dup in eliminar:
                    print(f"  ELIMINAR -> ID {dup.id}: {dup.nit:15s} | {dup.razon_social[:40]:40s}")
                    print(f"              Area: {(dup.area or 'N/A')[:15]:15s} | Email: {('Si' if dup.contacto_email else 'No'):3s}")

                print(f"  Referencias:")
                print(f"    Facturas: {resultado['facturas_actualizadas']}")
                print(f"    Asignaciones: {resultado['asignaciones_actualizadas']}")

                self.grupos_duplicados.append(resultado)
                self.facturas_actualizadas += resultado['facturas_actualizadas']
                self.asignaciones_actualizadas += resultado['asignaciones_actualizadas']

            # Aplicar
            print(f"\n[3] Aplicando cambios...")

            if not self.dry_run:
                # Eliminar duplicados
                for resultado in self.grupos_duplicados:
                    for dup in resultado['eliminar']:
                        self.db.delete(dup)
                        self.registros_eliminados += 1

                self.db.commit()
                print(f"   Cambios aplicados correctamente")
            else:
                for resultado in self.grupos_duplicados:
                    self.registros_eliminados += len(resultado['eliminar'])
                print(f"   DRY RUN: Sin cambios")

            # Reporte
            self.generar_reporte()

            return True

        except Exception as e:
            print(f"\nERROR: {str(e)}")
            if not self.dry_run:
                self.db.rollback()
            return False
        finally:
            self.db.close()

    def generar_reporte(self):
        """Genera reporte final."""
        print("\n" + "="*70)
        print("REPORTE FINAL")
        print("="*70)

        print(f"\nESTADISTICAS:")
        print(f"  Grupos duplicados: {len(self.grupos_duplicados)}")
        print(f"  Registros eliminados: {self.registros_eliminados}")
        print(f"  Facturas actualizadas: {self.facturas_actualizadas}")
        print(f"  Asignaciones actualizadas: {self.asignaciones_actualizadas}")

        if not self.dry_run:
            total = self.db.query(func.count(Proveedor.id)).scalar()
            print(f"\nESTADO FINAL:")
            print(f"  Total proveedores: {total}")

        print("\n" + "="*70)
        print("FUSION " + ("SIMULADA" if self.dry_run else "COMPLETADA"))
        print("="*70 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Fusiona proveedores duplicados'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Modo simulacion'
    )

    args = parser.parse_args()

    fusionador = FusionadorDuplicados(dry_run=args.dry_run)
    success = fusionador.ejecutar()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
