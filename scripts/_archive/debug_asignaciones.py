"""
Script para debuggear la distribución de asignaciones en AsignacionNitResponsable
"""
from app.db.session import SessionLocal
from app.models.responsable import Responsable
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.factura import Factura
from sqlalchemy import func

db = SessionLocal()

try:
    print("\n" + "="*80)
    print("DEBUG: DISTRIBUCIÓN DE ASIGNACIONES")
    print("="*80)

    # 1. Ver responsables
    print("\n1. RESPONSABLES EN EL SISTEMA:")
    responsables = db.query(Responsable).all()
    for resp in responsables:
        print(f"   ID: {resp.id}, Usuario: '{resp.usuario}', Nombre: {resp.nombre}")

    # 2. Ver asignaciones por responsable
    print("\n2. ASIGNACIONES EN AsignacionNitResponsable:")
    for resp in responsables:
        asignaciones = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.responsable_id == resp.id,
            AsignacionNitResponsable.activo == True
        ).all()

        print(f"\n   {resp.nombre} (ID: {resp.id})")
        print(f"   Total asignaciones activas: {len(asignaciones)}")
        if asignaciones:
            print(f"   Primeras 5:")
            for asig in asignaciones[:5]:
                print(f"     - {asig.nit}: {asig.nombre_proveedor}")
            if len(asignaciones) > 5:
                print(f"     ... y {len(asignaciones) - 5} más")

    # 3. Ver facturas por responsable
    print("\n3. FACTURAS EN LA TABLA (donde responsable_id != NULL):")
    for resp in responsables:
        total_facturas = db.query(func.count(Factura.id)).filter(
            Factura.responsable_id == resp.id
        ).scalar()

        print(f"\n   {resp.nombre} (ID: {resp.id})")
        print(f"   Total facturas con responsable_id = {resp.id}: {total_facturas}")

        # Mostrar primeras 3 facturas
        if total_facturas > 0:
            facturas_muestra = db.query(Factura).filter(
                Factura.responsable_id == resp.id
            ).limit(3).all()
            print(f"   Primeras 3 facturas:")
            for fac in facturas_muestra:
                print(f"     - {fac.numero_factura}: {fac.monto_total} ({fac.estado})")

    # 4. Verificar inconsistencias
    print("\n4. VERIFICAR INCONSISTENCIAS:")
    print("   Facturas donde responsable_id != NULL pero NO hay asignación en AsignacionNitResponsable:")

    # Subquery: obtener todos los responsables_id que tienen al menos 1 asignación
    respons_con_asignacion = db.query(AsignacionNitResponsable.responsable_id).distinct()

    facturas_inconsistentes = db.query(Factura).filter(
        Factura.responsable_id.notin_(respons_con_asignacion)
    ).limit(5).all()

    if facturas_inconsistentes:
        for fac in facturas_inconsistentes:
            resp = db.query(Responsable).filter(Responsable.id == fac.responsable_id).first()
            print(f"     - Factura {fac.numero_factura}: responsable_id={fac.responsable_id} ({resp.nombre if resp else 'Unknown'}), pero NO hay asignación")
    else:
        print(f"     (Ninguna inconsistencia encontrada)")

    print("\n" + "="*80)

finally:
    db.close()
