#!/usr/bin/env python
"""
Script: Actualiza los estados de asignación de todas las facturas
Recalcula estado_asignacion basándose en responsable_id y accion_por
"""

import sys
from pathlib import Path

backend_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, backend_dir)

import os
os.chdir(backend_dir)

from app.db.session import SessionLocal
from app.models.factura import Factura, EstadoAsignacion
from datetime import datetime

def actualizar_estados_asignacion():
    """Recalcula los estados de asignación para todas las facturas"""
    db = SessionLocal()

    print("\n" + "="*80)
    print("ACTUALIZACION: Estados de asignacion de facturas")
    print("="*80)
    print(f"Fecha/Hora: {datetime.now().isoformat()}\n")

    try:
        # Obtener todas las facturas
        todas_facturas = db.query(Factura).all()
        print(f"Total de facturas: {len(todas_facturas)}")

        # Recalcular estados
        cambios = 0
        estados_antes = {}
        estados_despues = {}

        for factura in todas_facturas:
            # Registrar estado anterior
            estado_anterior = factura.estado_asignacion.value if factura.estado_asignacion else "NONE"
            if estado_anterior not in estados_antes:
                estados_antes[estado_anterior] = 0
            estados_antes[estado_anterior] += 1

            # Recalcular estado
            nuevo_estado = factura.calcular_estado_asignacion()

            # Actualizar si cambió
            if factura.estado_asignacion != nuevo_estado:
                factura.estado_asignacion = nuevo_estado
                cambios += 1

            # Registrar estado nuevo
            estado_nuevo = nuevo_estado.value if nuevo_estado else "NONE"
            if estado_nuevo not in estados_despues:
                estados_despues[estado_nuevo] = 0
            estados_despues[estado_nuevo] += 1

        db.commit()

        print(f"Estados actualizados: {cambios}")
        print(f"\nEstados ANTES:")
        for estado, cantidad in sorted(estados_antes.items()):
            pct = (cantidad / len(todas_facturas) * 100) if todas_facturas else 0
            print(f"  {estado:20} {cantidad:8} ({pct:5.1f}%)")

        print(f"\nEstados DESPUES:")
        for estado, cantidad in sorted(estados_despues.items()):
            pct = (cantidad / len(todas_facturas) * 100) if todas_facturas else 0
            print(f"  {estado:20} {cantidad:8} ({pct:5.1f}%)")

        print(f"\n[OK] Estados de asignacion actualizados exitosamente")
        print("="*80)

        return True

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = actualizar_estados_asignacion()
    sys.exit(0 if success else 1)
