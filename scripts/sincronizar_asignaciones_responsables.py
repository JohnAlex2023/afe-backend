"""
Script para sincronizar las dos tablas de asignaciones:
- responsable_proveedor (tabla vieja, la que muestra la interfaz)
- asignacion_nit_responsable (tabla nueva, la que usa el workflow)

Este script:
1. Lee las asignaciones de responsable_proveedor
2. Crea o actualiza las asignaciones correspondientes en asignacion_nit_responsable
3. Actualiza el responsable_id en todas las facturas afectadas
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.responsable_proveedor import ResponsableProveedor
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.responsable import Responsable
from app.models.proveedor import Proveedor
from app.models.factura import Factura

def sincronizar_asignaciones():
    """
    Sincroniza responsable_proveedor -> asignacion_nit_responsable
    """
    db: Session = SessionLocal()

    try:
        print("\n" + "="*80)
        print("SINCRONIZACION DE TABLAS DE ASIGNACIONES")
        print("="*80 + "\n")

        # 1. Obtener todas las relaciones activas de responsable_proveedor
        relaciones = db.query(ResponsableProveedor).filter(
            ResponsableProveedor.activo == True
        ).all()

        print(f"[INFO] Relaciones en responsable_proveedor: {len(relaciones)}")

        stats = {
            'total': len(relaciones),
            'creadas': 0,
            'actualizadas': 0,
            'sin_cambio': 0,
            'sin_nit': 0,
            'errores': 0
        }

        facturas_actualizadas_total = 0

        # 2. Procesar cada relación
        for idx, rel in enumerate(relaciones, 1):
            try:
                # Obtener proveedor
                proveedor = db.query(Proveedor).filter(
                    Proveedor.id == rel.proveedor_id
                ).first()

                if not proveedor or not proveedor.nit:
                    stats['sin_nit'] += 1
                    continue

                # Obtener responsable
                responsable = db.query(Responsable).filter(
                    Responsable.id == rel.responsable_id
                ).first()

                if not responsable:
                    continue

                # Buscar si existe asignación NIT
                asignacion = db.query(AsignacionNitResponsable).filter(
                    AsignacionNitResponsable.nit == proveedor.nit
                ).first()

                if asignacion:
                    # Ya existe - actualizar si es diferente
                    if asignacion.responsable_id != rel.responsable_id:
                        print(f"[UPDATE] {proveedor.razon_social[:40]:40} | {proveedor.nit:15} | {responsable.nombre}")

                        asignacion.responsable_id = rel.responsable_id
                        asignacion.nombre_proveedor = proveedor.razon_social
                        asignacion.activo = True

                        # Actualizar facturas del proveedor
                        facturas = db.query(Factura).filter(
                            Factura.proveedor_id == proveedor.id
                        ).all()

                        for factura in facturas:
                            factura.responsable_id = rel.responsable_id

                        facturas_actualizadas_total += len(facturas)
                        stats['actualizadas'] += 1
                    else:
                        stats['sin_cambio'] += 1

                else:
                    # No existe - crear nueva
                    print(f"[CREATE] {proveedor.razon_social[:40]:40} | {proveedor.nit:15} | {responsable.nombre}")

                    nueva_asignacion = AsignacionNitResponsable(
                        nit=proveedor.nit,
                        nombre_proveedor=proveedor.razon_social,
                        responsable_id=rel.responsable_id,
                        area=responsable.area or "General",
                        permitir_aprobacion_automatica=True,
                        activo=True
                    )

                    db.add(nueva_asignacion)

                    # Actualizar facturas del proveedor
                    facturas = db.query(Factura).filter(
                        Factura.proveedor_id == proveedor.id
                    ).all()

                    for factura in facturas:
                        factura.responsable_id = rel.responsable_id

                    facturas_actualizadas_total += len(facturas)
                    stats['creadas'] += 1

                # Commit cada 20 registros
                if idx % 20 == 0:
                    db.commit()
                    print(f"[PROGRESS] Procesadas {idx}/{stats['total']} relaciones...")

            except Exception as e:
                print(f"[ERROR] Error procesando relación ID {rel.id}: {str(e)}")
                stats['errores'] += 1
                continue

        # 3. Commit final
        db.commit()

        # 4. Mostrar resumen
        print("\n" + "="*80)
        print("RESUMEN DE SINCRONIZACION")
        print("="*80)
        print(f"Total relaciones procesadas:       {stats['total']}")
        print(f"Asignaciones CREADAS:              {stats['creadas']} [NUEVO]")
        print(f"Asignaciones ACTUALIZADAS:         {stats['actualizadas']} [UPDATED]")
        print(f"Sin cambio:                        {stats['sin_cambio']}")
        print(f"Sin NIT:                           {stats['sin_nit']}")
        print(f"Errores:                           {stats['errores']}")
        print(f"\nFacturas actualizadas:             {facturas_actualizadas_total}")
        print("="*80)

        print("\n[OK] Sincronizacion completada exitosamente\n")

    except Exception as e:
        print(f"\n[ERROR] Error general: {str(e)}")
        db.rollback()
        raise

    finally:
        db.close()

if __name__ == "__main__":
    print("\nEste script sincronizara las asignaciones de responsable_proveedor")
    print("hacia asignacion_nit_responsable y actualizara todas las facturas.\n")

    confirmar = input("Deseas continuar? (escribe 'SI' para confirmar): ")

    if confirmar.upper() == "SI":
        sincronizar_asignaciones()
    else:
        print("\n[INFO] Operacion cancelada\n")
