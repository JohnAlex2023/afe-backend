"""
Script para RE-SINCRONIZAR responsables de TODAS las facturas basándose en las asignaciones NIT actuales.

Este script:
1. Lee todas las facturas (tengan o no responsable asignado)
2. Obtiene el NIT del proveedor de cada factura
3. Busca la asignación ACTUAL del responsable para ese NIT
4. Actualiza el campo responsable_id de la factura con la asignación actual

Útil cuando cambias asignaciones NIT -> Responsable y necesitas actualizar facturas existentes.
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.proveedor import Proveedor
from app.models.workflow_aprobacion import AsignacionNitResponsable

def resincronizar_responsables():
    """
    Re-sincroniza TODAS las facturas con las asignaciones NIT actuales.
    """
    db: Session = SessionLocal()

    try:
        print("\n" + "="*80)
        print("RE-SINCRONIZACIÓN DE RESPONSABLES EN FACTURAS")
        print("="*80 + "\n")

        # 1. Obtener TODAS las facturas (no solo las sin responsable)
        facturas = db.query(Factura).all()

        print(f"[INFO] Total de facturas a procesar: {len(facturas)}")

        if len(facturas) == 0:
            print("[OK] No hay facturas para procesar")
            return

        # Estadísticas
        stats = {
            'total': len(facturas),
            'actualizadas': 0,
            'sin_cambio': 0,
            'sin_proveedor': 0,
            'sin_nit': 0,
            'sin_asignacion': 0,
            'errores': 0
        }

        cambios_por_responsable = {}

        # 2. Procesar cada factura
        for idx, factura in enumerate(facturas, 1):
            try:
                # Obtener proveedor
                if not factura.proveedor_id:
                    stats['sin_proveedor'] += 1
                    continue

                proveedor = db.query(Proveedor).filter(
                    Proveedor.id == factura.proveedor_id
                ).first()

                if not proveedor:
                    stats['sin_proveedor'] += 1
                    continue

                if not proveedor.nit:
                    stats['sin_nit'] += 1
                    continue

                # Buscar asignación ACTUAL NIT -> Responsable
                asignacion = db.query(AsignacionNitResponsable).filter(
                    AsignacionNitResponsable.nit == proveedor.nit,
                    AsignacionNitResponsable.activo == True
                ).first()

                if not asignacion:
                    stats['sin_asignacion'] += 1
                    continue

                # Verificar si hay cambio
                responsable_anterior = factura.responsable_id
                responsable_nuevo = asignacion.responsable_id

                if responsable_anterior == responsable_nuevo:
                    stats['sin_cambio'] += 1
                else:
                    # Actualizar responsable
                    factura.responsable_id = responsable_nuevo
                    stats['actualizadas'] += 1

                    # Contabilizar cambio
                    key = f"{responsable_anterior} -> {responsable_nuevo}"
                    cambios_por_responsable[key] = cambios_por_responsable.get(key, 0) + 1

                    # Log cada 10 cambios
                    if stats['actualizadas'] % 10 == 0:
                        print(f"[PROGRESS] {stats['actualizadas']} facturas actualizadas...")

            except Exception as e:
                print(f"[ERROR] Error procesando factura {factura.numero_factura}: {str(e)}")
                stats['errores'] += 1
                continue

        # 3. Guardar cambios
        if stats['actualizadas'] > 0:
            db.commit()
            print(f"\n[OK] Cambios guardados en la base de datos")
        else:
            print(f"\n[INFO] No hubo cambios que guardar")

        # 4. Mostrar resumen
        print("\n" + "="*80)
        print("RESUMEN DE RE-SINCRONIZACIÓN")
        print("="*80)
        print(f"Total facturas procesadas:         {stats['total']}")
        print(f"Facturas ACTUALIZADAS:             {stats['actualizadas']} [OK]")
        print(f"Facturas sin cambio:               {stats['sin_cambio']}")
        print(f"Sin proveedor:                     {stats['sin_proveedor']}")
        print(f"Sin NIT:                           {stats['sin_nit']}")
        print(f"Sin asignacion NIT:                {stats['sin_asignacion']}")
        print(f"Errores:                           {stats['errores']}")
        print("="*80)

        # Mostrar cambios por responsable
        if cambios_por_responsable:
            print("\n" + "="*80)
            print("CAMBIOS POR RESPONSABLE")
            print("="*80)
            for cambio, cantidad in cambios_por_responsable.items():
                print(f"{cambio:30} | {cantidad} facturas")
            print("="*80)

        # Calcular porcentaje
        if stats['total'] > 0:
            porcentaje = ((stats['actualizadas'] + stats['sin_cambio']) / stats['total']) * 100
            print(f"\n[RESULTADO] {porcentaje:.1f}% de facturas con responsable correcto")

        print("\n[OK] Proceso completado exitosamente\n")

    except Exception as e:
        print(f"\n[ERROR] Error general: {str(e)}")
        db.rollback()
        raise

    finally:
        db.close()

if __name__ == "__main__":
    print("\nADVERTENCIA: Este script actualizara el responsable de TODAS las facturas")
    print("segun las asignaciones NIT actuales en la tabla asignacion_nit_responsable.\n")

    confirmar = input("Deseas continuar? (escribe 'SI' para confirmar): ")

    if confirmar.upper() == "SI":
        resincronizar_responsables()
    else:
        print("\n[INFO] Operación cancelada\n")
