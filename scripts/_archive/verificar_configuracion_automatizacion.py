"""
Script para verificar la configuracion necesaria para la automatizacion.

Uso:
    python -m scripts.verificar_configuracion_automatizacion
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


def verificar_configuracion(db: Session):
    """Verifica la configuracion de automatizacion."""
    print("\n" + "=" * 80)
    print("VERIFICACION DE CONFIGURACION PARA AUTOMATIZACION")
    print("=" * 80)

    # 1. Responsables en el sistema
    print("\n[1] RESPONSABLES REGISTRADOS:")
    print("-" * 80)

    responsables = db.query(Responsable).all()
    print(f"Total responsables: {len(responsables)}")

    if responsables:
        for r in responsables:
            print(f"\n  ID: {r.id}")
            print(f"  Nombre: {r.nombre}")
            print(f"  Email: {r.email}")
            print(f"  Rol: {r.role.nombre if r.role else 'N/A'}")
            print(f"  Activo: {r.activo}")
    else:
        print("\n  [!] NO HAY RESPONSABLES REGISTRADOS")
        print("      La automatizacion necesita responsables para asignar facturas.")

    # 2. Asignaciones NIT -> Responsable
    print("\n[2] ASIGNACIONES NIT -> RESPONSABLE:")
    print("-" * 80)

    asignaciones = db.query(AsignacionNitResponsable).all()
    print(f"Total asignaciones configuradas: {len(asignaciones)}")

    if asignaciones:
        print("\n  Configuracion de asignaciones:")
        for asig in asignaciones[:10]:  # Mostrar primeras 10
            resp = db.query(Responsable).get(asig.responsable_id)
            print(f"\n  NIT: {asig.nit}")
            print(f"    Proveedor: {asig.nombre_proveedor or 'N/A'}")
            print(f"    Responsable: {resp.nombre if resp else 'N/A'}")
            print(f"    Area: {asig.area or 'N/A'}")
            print(f"    Aprobacion automatica: {asig.permitir_aprobacion_automatica}")
            print(f"    Requiere revision siempre: {asig.requiere_revision_siempre}")
            print(f"    Activo: {asig.activo}")

        if len(asignaciones) > 10:
            print(f"\n  ... y {len(asignaciones) - 10} asignaciones mas")
    else:
        print("\n  [!] NO HAY ASIGNACIONES NIT -> RESPONSABLE")
        print("      Necesitas configurar que responsable aprueba cada NIT.")

    # 3. NITs de proveedores en facturas vs NITs configurados
    print("\n[3] COBERTURA DE NITS:")
    print("-" * 80)

    # NITs unicos en facturas
    nits_facturas = db.query(Proveedor.nit)\
        .join(Factura, Factura.proveedor_id == Proveedor.id)\
        .distinct().all()
    nits_facturas = {nit[0].replace('-', '').strip() for nit in nits_facturas}

    # NITs configurados en asignaciones
    nits_configurados = {asig.nit.replace('-', '').strip() for asig in asignaciones}

    print(f"NITs unicos en facturas: {len(nits_facturas)}")
    print(f"NITs con responsable asignado: {len(nits_configurados)}")

    nits_sin_asignar = nits_facturas - nits_configurados
    cobertura = ((len(nits_facturas) - len(nits_sin_asignar)) / len(nits_facturas) * 100) if nits_facturas else 0

    print(f"Cobertura: {cobertura:.1f}%")

    if nits_sin_asignar:
        print(f"\n  [!] NITs SIN RESPONSABLE ASIGNADO ({len(nits_sin_asignar)}):")
        for nit in sorted(list(nits_sin_asignar))[:15]:
            # Buscar proveedor
            prov = db.query(Proveedor).filter(
                Proveedor.nit.like(f"%{nit}%")
            ).first()
            if prov:
                facturas_count = db.query(Factura).filter(
                    Factura.proveedor_id == prov.id
                ).count()
                print(f"    - {nit:15s} | {prov.razon_social[:40]:40s} | {facturas_count} facturas")

        if len(nits_sin_asignar) > 15:
            print(f"    ... y {len(nits_sin_asignar) - 15} NITs mas")

    # 4. Facturas con historial (para comparacion)
    print("\n[4] HISTORIAL DE FACTURAS (para automatizacion):")
    print("-" * 80)

    # Verificar si hay facturas de meses anteriores para comparar
    from sqlalchemy import func, extract
    from datetime import datetime

    mes_actual = datetime.now().month
    anio_actual = datetime.now().year

    facturas_mes_actual = db.query(Factura).filter(
        extract('month', Factura.fecha_emision) == mes_actual,
        extract('year', Factura.fecha_emision) == anio_actual
    ).count()

    facturas_mes_anterior = db.query(Factura).filter(
        extract('month', Factura.fecha_emision) == mes_actual - 1 if mes_actual > 1 else 12,
        extract('year', Factura.fecha_emision) == anio_actual if mes_actual > 1 else anio_actual - 1
    ).count()

    print(f"Facturas del mes actual: {facturas_mes_actual}")
    print(f"Facturas del mes anterior: {facturas_mes_anterior}")

    if facturas_mes_anterior > 0:
        print("\n  [OK] Hay facturas del mes anterior para comparar")
    else:
        print("\n  [!] No hay facturas del mes anterior")
        print("      La automatizacion necesita facturas previas para comparar")

    # 5. Endpoint de automatizacion
    print("\n[5] COMO EJECUTAR LA AUTOMATIZACION:")
    print("-" * 80)
    print("\n  Opcion 1: Via API")
    print("    POST http://localhost:8000/api/v1/automatizacion/procesar")
    print("    Body: { \"mes\": 10, \"anio\": 2025 }")
    print("\n  Opcion 2: Via script Python")
    print("    python -m scripts.ejecutar_automatizacion")


def main():
    """Funcion principal."""
    db = SessionLocal()
    try:
        verificar_configuracion(db)
        print("\n" + "=" * 80)
        print("[OK] Verificacion completada")
        print("=" * 80 + "\n")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
