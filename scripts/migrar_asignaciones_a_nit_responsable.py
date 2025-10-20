"""
Script para migrar asignaciones de responsable_proveedor a asignacion_nit_responsable

Este script:
1. Lee todas las asignaciones en responsable_proveedor que estan activas
2. Para cada asignacion, crea o actualiza un registro en asignacion_nit_responsable
3. Evita duplicados usando el NIT como clave unica
"""
import sys
import os
from pathlib import Path

# Agregar el directorio raiz al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.responsable_proveedor import ResponsableProveedor
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.proveedor import Proveedor

def migrar_asignaciones():
    """Migra asignaciones de responsable_proveedor a asignacion_nit_responsable"""
    db: Session = SessionLocal()

    try:
        print("\n" + "="*80)
        print("MIGRACION: responsable_proveedor -> asignacion_nit_responsable")
        print("="*80 + "\n")

        # Obtener todas las asignaciones activas en responsable_proveedor
        asignaciones_origen = db.query(ResponsableProveedor).filter(
            ResponsableProveedor.activo == True
        ).all()

        print(f"[INFO] Asignaciones encontradas en responsable_proveedor: {len(asignaciones_origen)}\n")

        stats = {
            'total': len(asignaciones_origen),
            'creadas': 0,
            'actualizadas': 0,
            'duplicadas': 0,
            'sin_nit': 0,
            'errores': 0
        }

        for asig in asignaciones_origen:
            try:
                # Obtener proveedor
                proveedor = db.query(Proveedor).filter(
                    Proveedor.id == asig.proveedor_id
                ).first()

                if not proveedor:
                    print(f"[WARN] Proveedor ID {asig.proveedor_id} no encontrado")
                    stats['errores'] += 1
                    continue

                if not proveedor.nit:
                    print(f"[WARN] Proveedor {proveedor.razon_social} sin NIT")
                    stats['sin_nit'] += 1
                    continue

                # Verificar si ya existe asignacion NIT para este responsable
                asignacion_existente = db.query(AsignacionNitResponsable).filter(
                    AsignacionNitResponsable.nit == proveedor.nit
                ).first()

                if asignacion_existente:
                    # Si existe pero para otro responsable, verificar cual tiene prioridad
                    if asignacion_existente.responsable_id != asig.responsable_id:
                        print(f"\n[CONFLICT] NIT {proveedor.nit} ya asignado:")
                        print(f"  Existente: Responsable ID {asignacion_existente.responsable_id}")
                        print(f"  Nuevo: Responsable ID {asig.responsable_id}")
                        print(f"  DECISION: Manteniendo asignacion existente")
                        stats['duplicadas'] += 1
                    else:
                        # Ya existe para el mismo responsable, solo actualizar datos
                        asignacion_existente.nombre_proveedor = proveedor.razon_social
                        asignacion_existente.activo = True
                        db.add(asignacion_existente)
                        stats['actualizadas'] += 1
                        print(f"[UPDATE] NIT {proveedor.nit:20} -> Responsable ID {asig.responsable_id}")
                else:
                    # Crear nueva asignacion
                    nueva_asignacion = AsignacionNitResponsable(
                        nit=proveedor.nit,
                        nombre_proveedor=proveedor.razon_social,
                        responsable_id=asig.responsable_id,
                        activo=True,
                        permitir_aprobacion_automatica=True,
                        requiere_revision_siempre=False
                    )
                    db.add(nueva_asignacion)
                    stats['creadas'] += 1
                    print(f"[CREATE] NIT {proveedor.nit:20} -> Responsable ID {asig.responsable_id} ({proveedor.razon_social})")

            except Exception as e:
                print(f"[ERROR] Error procesando asignacion: {str(e)}")
                stats['errores'] += 1
                continue

        # Commit cambios
        db.commit()

        # Resumen
        print("\n" + "="*80)
        print("RESUMEN DE MIGRACION")
        print("="*80)
        print(f"Total asignaciones procesadas:    {stats['total']}")
        print(f"Nuevas asignaciones CREADAS:      {stats['creadas']} [OK]")
        print(f"Asignaciones ACTUALIZADAS:        {stats['actualizadas']}")
        print(f"Duplicadas (mantenidas):          {stats['duplicadas']}")
        print(f"Sin NIT:                          {stats['sin_nit']}")
        print(f"Errores:                          {stats['errores']}")
        print("="*80)

        print("\n[OK] Migracion completada exitosamente\n")

    except Exception as e:
        print(f"\n[ERROR] Error general: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    print("\nEste script migrara asignaciones de responsable_proveedor a asignacion_nit_responsable")
    print("NOTA: Si un NIT ya esta asignado, se mantendra la asignacion existente.\n")

    confirmar = input("Deseas continuar? (escribe 'SI' para confirmar): ")

    if confirmar.upper() == "SI":
        migrar_asignaciones()
    else:
        print("\n[INFO] Operacion cancelada\n")
