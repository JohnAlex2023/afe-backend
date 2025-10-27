"""
Script para sincronizar facturas con las asignaciones de AsignacionNitResponsable

Este script asegura que cada factura esté asignada al responsable correcto
basado en los NITs asignados en AsignacionNitResponsable.

Uso:
    python scripts/sincronizar_facturas_con_asignaciones.py
"""
from app.db.session import SessionLocal
from app.models.responsable import Responsable
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.factura import Factura
from app.models.proveedor import Proveedor
from sqlalchemy import func

db = SessionLocal()

try:
    print("\n" + "="*80)
    print("SINCRONIZANDO FACTURAS CON ASIGNACIONES DE NITs")
    print("="*80)

    # Obtener todos los responsables
    responsables = db.query(Responsable).all()

    total_actualizadas = 0
    total_ignoradas = 0
    total_sin_asignacion = 0

    for resp in responsables:
        print(f"\n--- {resp.nombre} (ID: {resp.id}) ---")

        # 1. Obtener NITs asignados a este responsable
        asignaciones = db.query(AsignacionNitResponsable.nit).filter(
            AsignacionNitResponsable.responsable_id == resp.id,
            AsignacionNitResponsable.activo == True
        ).all()

        nits_asignados = [nit for (nit,) in asignaciones if nit]

        if not nits_asignados:
            print(f"   Sin NITs asignados")
            continue

        # 2. Obtener IDs de proveedores con esos NITs
        proveedor_ids = db.query(Proveedor.id).filter(
            Proveedor.nit.in_(nits_asignados)
        ).all()
        proveedor_ids = [pid for (pid,) in proveedor_ids]

        if not proveedor_ids:
            print(f"   {len(nits_asignados)} NITs asignados pero NO hay proveedores en BD")
            continue

        # 3. Obtener facturas de esos proveedores
        facturas = db.query(Factura).filter(
            Factura.proveedor_id.in_(proveedor_ids)
        ).all()

        print(f"   NITs asignados: {len(nits_asignados)}")
        print(f"   Proveedores en BD: {len(proveedor_ids)}")
        print(f"   Facturas de esos proveedores: {len(facturas)}")

        # 4. Actualizar facturas que NO tienen el responsable correcto
        actualizadas_ahora = 0
        ignoradas_ahora = 0

        for factura in facturas:
            if factura.responsable_id == resp.id:
                # Ya está correctamente asignada
                ignoradas_ahora += 1
            else:
                # Actualizar la asignación
                responsable_anterior = db.query(Responsable).filter(
                    Responsable.id == factura.responsable_id
                ).first() if factura.responsable_id else None

                print(f"   ✓ Factura {factura.numero_factura}:")
                if responsable_anterior:
                    print(f"     De: {responsable_anterior.nombre} → A: {resp.nombre}")
                else:
                    print(f"     De: (sin asignar) → A: {resp.nombre}")

                factura.responsable_id = resp.id
                actualizadas_ahora += 1

        if actualizadas_ahora > 0:
            db.flush()

        print(f"\n   Resumen: {actualizadas_ahora} actualizadas, {ignoradas_ahora} ya correctas")
        total_actualizadas += actualizadas_ahora
        total_ignoradas += ignoradas_ahora

    # Commit
    db.commit()

    print(f"\n" + "="*80)
    print(f"SINCRONIZACIÓN COMPLETADA")
    print(f"="*80)
    print(f"Total facturas actualizadas: {total_actualizadas}")
    print(f"Total facturas ya correctas: {total_ignoradas}")
    print(f"✓ Cambios guardados en la base de datos")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
