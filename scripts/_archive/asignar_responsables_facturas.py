"""
Script para asignar responsables a facturas existentes basándose en el NIT del proveedor.

Este script:
1. Busca todas las facturas sin responsable asignado
2. Obtiene el NIT del proveedor de cada factura
3. Busca el responsable asignado a ese NIT en la tabla asignacion_nit_responsable
4. Actualiza el campo responsable_id de la factura
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

def asignar_responsables_facturas():
    """
    Asigna responsables a facturas existentes basándose en el NIT del proveedor.
    """
    db: Session = SessionLocal()

    try:
        print("\n" + "="*80)
        print("ASIGNACION DE RESPONSABLES A FACTURAS EXISTENTES")
        print("="*80 + "\n")

        # 1. Obtener todas las facturas sin responsable
        facturas_sin_responsable = db.query(Factura).filter(
            Factura.responsable_id.is_(None)
        ).all()

        print(f"[INFO] Facturas sin responsable: {len(facturas_sin_responsable)}")

        if len(facturas_sin_responsable) == 0:
            print("[OK] Todas las facturas ya tienen responsable asignado")
            return

        # Estadísticas
        stats = {
            'total': len(facturas_sin_responsable),
            'asignadas': 0,
            'sin_proveedor': 0,
            'sin_nit': 0,
            'sin_asignacion': 0,
            'errores': 0
        }

        # 2. Procesar cada factura
        for idx, factura in enumerate(facturas_sin_responsable, 1):
            try:
                # Obtener proveedor
                if not factura.proveedor_id:
                    print(f"[WARN] Factura {factura.numero_factura} no tiene proveedor")
                    stats['sin_proveedor'] += 1
                    continue

                proveedor = db.query(Proveedor).filter(
                    Proveedor.id == factura.proveedor_id
                ).first()

                if not proveedor:
                    print(f"[WARN] Proveedor ID {factura.proveedor_id} no encontrado")
                    stats['sin_proveedor'] += 1
                    continue

                if not proveedor.nit:
                    print(f"[WARN] Proveedor {proveedor.nombre} no tiene NIT")
                    stats['sin_nit'] += 1
                    continue

                # Buscar asignación NIT -> Responsable
                asignacion = db.query(AsignacionNitResponsable).filter(
                    AsignacionNitResponsable.nit == proveedor.nit,
                    AsignacionNitResponsable.activo == True
                ).first()

                if not asignacion:
                    print(f"[WARN] No hay asignación para NIT {proveedor.nit} ({proveedor.nombre})")
                    stats['sin_asignacion'] += 1
                    continue

                # Asignar responsable
                factura.responsable_id = asignacion.responsable_id
                stats['asignadas'] += 1

                # Mostrar progreso cada 50 facturas
                if idx % 50 == 0:
                    print(f"[PROGRESS] Procesadas {idx}/{stats['total']} facturas...")

            except Exception as e:
                print(f"[ERROR] Error procesando factura {factura.numero_factura}: {str(e)}")
                stats['errores'] += 1
                continue

        # 3. Guardar cambios
        db.commit()

        # 4. Mostrar resumen
        print("\n" + "="*80)
        print("RESUMEN DE ASIGNACION")
        print("="*80)
        print(f"Total facturas procesadas:        {stats['total']}")
        print(f"Facturas con responsable asignado: {stats['asignadas']} [OK]")
        print(f"Sin proveedor:                     {stats['sin_proveedor']}")
        print(f"Sin NIT:                           {stats['sin_nit']}")
        print(f"Sin asignacion NIT:                {stats['sin_asignacion']}")
        print(f"Errores:                           {stats['errores']}")
        print("="*80)

        # Calcular porcentaje de éxito
        if stats['total'] > 0:
            porcentaje = (stats['asignadas'] / stats['total']) * 100
            print(f"\n[RESULTADO] {porcentaje:.1f}% de facturas con responsable asignado")

        print("\n[OK] Proceso completado exitosamente\n")

    except Exception as e:
        print(f"\n[ERROR] Error general: {str(e)}")
        db.rollback()
        raise

    finally:
        db.close()

if __name__ == "__main__":
    asignar_responsables_facturas()
