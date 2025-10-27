"""
Script para asignar responsables a todos los NITs de proveedores.

Uso:
    python -m scripts.asignar_responsables_nits
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.responsable import Responsable
from app.models.proveedor import Proveedor
from app.models.factura import Factura
from datetime import datetime


def asignar_responsables_automatico(db: Session):
    """
    Asigna responsables a todos los NITs de proveedores que no tienen asignacion.

    Estrategia:
    - Obtener el primer responsable activo disponible
    - Asignar todos los NITs sin responsable a ese responsable
    - Permitir aprobacion automatica por defecto
    """
    print("\n" + "=" * 80)
    print("ASIGNACION AUTOMATICA DE RESPONSABLES A NITS")
    print("=" * 80)

    # 1. Obtener responsable por defecto
    responsable_default = db.query(Responsable).filter(
        Responsable.activo == True
    ).first()

    if not responsable_default:
        print("\n[ERROR] No hay responsables activos en el sistema")
        return

    print(f"\nResponsable por defecto: {responsable_default.nombre} ({responsable_default.email})")
    print(f"ID: {responsable_default.id}")

    # 2. Obtener NITs de facturas
    nits_facturas_query = db.query(Proveedor.nit, Proveedor.razon_social, Proveedor.id)\
        .join(Factura, Factura.proveedor_id == Proveedor.id)\
        .distinct()

    nits_facturas = []
    for nit, razon_social, prov_id in nits_facturas_query:
        nit_limpio = nit.replace('-', '').strip()
        nits_facturas.append({
            'nit': nit_limpio,
            'nit_original': nit,
            'razon_social': razon_social,
            'proveedor_id': prov_id
        })

    # 3. Obtener NITs ya configurados
    nits_configurados = {
        asig.nit.replace('-', '').strip()
        for asig in db.query(AsignacionNitResponsable).all()
    }

    # 4. Filtrar NITs sin asignar
    nits_sin_asignar = [
        nit_data for nit_data in nits_facturas
        if nit_data['nit'] not in nits_configurados
    ]

    print(f"\nTotal NITs en facturas: {len(nits_facturas)}")
    print(f"NITs ya configurados: {len(nits_configurados)}")
    print(f"NITs sin asignar: {len(nits_sin_asignar)}")

    if not nits_sin_asignar:
        print("\n[OK] Todos los NITs ya tienen responsable asignado!")
        return

    # 5. Crear asignaciones
    print(f"\nCreando asignaciones para {len(nits_sin_asignar)} NITs...")
    print("-" * 80)

    asignaciones_creadas = 0
    for nit_data in nits_sin_asignar:
        # Contar cuantas facturas tiene este proveedor
        facturas_count = db.query(Factura).filter(
            Factura.proveedor_id == nit_data['proveedor_id']
        ).count()

        nueva_asignacion = AsignacionNitResponsable(
            nit=nit_data['nit_original'],
            nombre_proveedor=nit_data['razon_social'],
            responsable_id=responsable_default.id,
            area="General",
            permitir_aprobacion_automatica=True,
            requiere_revision_siempre=False,
            monto_maximo_auto_aprobacion=None,  # Sin limite
            porcentaje_variacion_permitido=5.0,  # 5% de variacion
            activo=True,
            creado_por="SEED_SCRIPT",
            creado_en=datetime.now(),
            actualizado_en=datetime.now()
        )

        db.add(nueva_asignacion)
        asignaciones_creadas += 1

        print(f"  [{asignaciones_creadas:2d}] {nit_data['nit_original']:15s} | "
              f"{nit_data['razon_social'][:45]:45s} | "
              f"{facturas_count:3d} facturas")

    # Commit
    db.commit()

    print("\n" + "=" * 80)
    print(f"[OK] {asignaciones_creadas} asignaciones creadas exitosamente")
    print("=" * 80)

    # 6. Resumen final
    print("\nRESUMEN FINAL:")
    print("-" * 80)

    total_asignaciones = db.query(AsignacionNitResponsable).count()
    asignaciones_activas = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.activo == True
    ).count()

    print(f"Total asignaciones en sistema: {total_asignaciones}")
    print(f"Asignaciones activas: {asignaciones_activas}")
    print(f"Cobertura: 100%")

    # Distribucion por responsable
    print("\nDistribucion por responsable:")
    from sqlalchemy import func
    distribucion = db.query(
        Responsable.nombre,
        func.count(AsignacionNitResponsable.id).label('cantidad')
    ).join(AsignacionNitResponsable, AsignacionNitResponsable.responsable_id == Responsable.id)\
     .group_by(Responsable.id).all()

    for nombre, cantidad in distribucion:
        print(f"  - {nombre:30s}: {cantidad} NITs")


def main():
    """Funcion principal."""
    db = SessionLocal()
    try:
        asignar_responsables_automatico(db)
        print("\n[OK] Proceso completado\n")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
