"""
RESOLVER DISTRIBUCIÓN DE NITs COMPARTIDOS

Problema: 25 NITs están asignados a múltiples responsables
Solución: Implementar regla de asignación basada en prioridad de responsable

Regla implementada:
1. Si un NIT está asignado a múltiples responsables
2. Asignar la factura al responsable más ANTIGUO en la asignación (por fecha)
3. Si tienen la misma fecha, usar el de menor ID

Esto asegura distribución consistente y reproducible.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.responsable import Responsable
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.factura import Factura
from app.models.proveedor import Proveedor
from sqlalchemy import func
from collections import defaultdict

db = SessionLocal()

def print_section(title):
    print("\n" + "="*120)
    print(f"  {title}")
    print("="*120)

try:
    print_section("RESOLVER DISTRIBUCIÓN DE NITs COMPARTIDOS")

    # Paso 1: Identificar todos los NITs compartidos
    print("\nPaso 1: Identificar NITs compartidos...")

    nits_por_responsable = defaultdict(list)

    asignaciones = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.activo == True
    ).all()

    for asig in asignaciones:
        nits_por_responsable[asig.nit].append({
            'responsable_id': asig.responsable_id,
            'fecha_creacion': asig.creado_en,
            'id': asig.id
        })

    nits_compartidos = {nit: resps for nit, resps in nits_por_responsable.items() if len(resps) > 1}

    print(f"  Total de NITs: {len(nits_por_responsable)}")
    print(f"  NITs compartidos (múltiples responsables): {len(nits_compartidos)}")
    print(f"  NITs únicos (un responsable): {len(nits_por_responsable) - len(nits_compartidos)}")

    # Paso 2: Para cada NIT compartido, determinar responsable PRINCIPAL
    print("\nPaso 2: Determinar responsable principal para cada NIT compartido...")

    responsable_principal_por_nit = {}

    for nit, asignaciones_list in nits_compartidos.items():
        # Ordenar por: fecha_creacion (ASC), luego por responsable_id (ASC)
        asignaciones_ordenadas = sorted(
            asignaciones_list,
            key=lambda x: (x['fecha_creacion'], x['responsable_id'])
        )

        responsable_principal = asignaciones_ordenadas[0]['responsable_id']
        responsable_principal_por_nit[nit] = {
            'responsable_id': responsable_principal,
            'alternativas': len(asignaciones_list)
        }

        resp_obj = db.query(Responsable).filter(Responsable.id == responsable_principal).first()
        print(f"  NIT {nit}: Principal = {resp_obj.nombre} ({len(asignaciones_list)} responsables)")

    # Paso 3: Reasignar TODAS las facturas basado en el responsable principal
    print("\nPaso 3: Reasignar facturas...")

    todas_las_facturas = db.query(Factura).all()
    facturas_actualizadas = 0
    facturas_sin_cambio = 0

    for factura in todas_las_facturas:
        if not factura.proveedor_id:
            continue

        proveedor = db.query(Proveedor).filter(Proveedor.id == factura.proveedor_id).first()
        if not proveedor or not proveedor.nit:
            continue

        nit = proveedor.nit

        # Determinar responsable correcto
        if nit in responsable_principal_por_nit:
            responsable_correcto_id = responsable_principal_por_nit[nit]['responsable_id']
        else:
            # NIT único, obtener de AsignacionNitResponsable
            asig = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == nit,
                AsignacionNitResponsable.activo == True
            ).first()

            if not asig:
                continue

            responsable_correcto_id = asig.responsable_id

        # Actualizar si es diferente
        if factura.responsable_id != responsable_correcto_id:
            resp_anterior = db.query(Responsable).filter(
                Responsable.id == factura.responsable_id
            ).first() if factura.responsable_id else None

            resp_nuevo = db.query(Responsable).filter(
                Responsable.id == responsable_correcto_id
            ).first()

            # Solo mostrar primeras 10
            if facturas_actualizadas < 10:
                print(f"  Factura {factura.numero_factura}: {resp_anterior.nombre if resp_anterior else 'NULL'} -> {resp_nuevo.nombre}")

            factura.responsable_id = responsable_correcto_id
            facturas_actualizadas += 1
        else:
            facturas_sin_cambio += 1

    if facturas_actualizadas > 10:
        print(f"  ... y {facturas_actualizadas - 10} más")

    if facturas_actualizadas > 0:
        db.flush()

    db.commit()

    # Paso 4: Verificar distribución final
    print("\nPaso 4: Distribución FINAL después de reasignación...")

    responsables = db.query(Responsable).all()

    for resp in responsables:
        total_facturas = db.query(func.count(Factura.id)).filter(
            Factura.responsable_id == resp.id
        ).scalar()

        asignaciones_nits = db.query(func.count(AsignacionNitResponsable.id)).filter(
            AsignacionNitResponsable.responsable_id == resp.id,
            AsignacionNitResponsable.activo == True
        ).scalar()

        # Contar cuántas facturas DEBERÍAN tener (basado en NITs asignados como principal)
        nits_como_principal = sum(1 for nit, principal in responsable_principal_por_nit.items()
                                   if principal['responsable_id'] == resp.id)

        nits_unicos = db.query(func.count(AsignacionNitResponsable.id)).filter(
            AsignacionNitResponsable.responsable_id == resp.id,
            AsignacionNitResponsable.activo == True,
            AsignacionNitResponsable.nit.notin_(
                [nit for nit in responsable_principal_por_nit.keys()]
            )
        ).scalar()

        nits_principales_reales = nits_como_principal + nits_unicos

        print(f"  {resp.nombre:15} | Facturas: {total_facturas:3} | NITs: {asignaciones_nits:2} " +
              f"| Como principal: {nits_como_principal:2} | Compartidos: {asignaciones_nits - nits_principales_reales:2}")

    print("\n" + "="*120)
    print("  RESUMEN")
    print("="*120)
    print(f"  Facturas reasignadas: {facturas_actualizadas}")
    print(f"  Facturas sin cambio: {facturas_sin_cambio}")
    print(f"  Total procesadas: {facturas_actualizadas + facturas_sin_cambio}")
    print("="*120)

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
