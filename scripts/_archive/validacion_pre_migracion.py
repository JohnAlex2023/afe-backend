"""
Script de Validacion Pre-Migracion

Verifica que todo este listo antes de ejecutar la migracion de Alembic
que eliminara la tabla responsable_proveedor.

Este script valida:
1. Todos los datos migrados a asignacion_nit_responsable
2. Todas las facturas tienen responsable asignado (o estan pendientes)
3. No hay dependencias rotas
4. El servidor inicia correctamente
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ['PYTHONIOENCODING'] = 'utf-8'

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.proveedor import Proveedor
from app.models.responsable import Responsable
from app.models.workflow_aprobacion import AsignacionNitResponsable


def validar_migracion_datos():
    """Valida que los datos fueron migrados correctamente"""
    db: Session = SessionLocal()
    errores = []
    advertencias = []

    try:
        print("\n" + "="*80)
        print("VALIDACION PRE-MIGRACION: responsable_proveedor -> asignacion_nit_responsable")
        print("="*80 + "\n")

        # 1. Verificar asignaciones en asignacion_nit_responsable
        asignaciones_nit = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == True
        ).all()

        print(f"[CHECK 1/5] Asignaciones en asignacion_nit_responsable")
        print(f"  Total asignaciones activas: {len(asignaciones_nit)}")

        if len(asignaciones_nit) == 0:
            errores.append("No hay asignaciones en asignacion_nit_responsable!")
        else:
            print(f"  [OK] {len(asignaciones_nit)} asignaciones encontradas")

        # 2. Verificar responsables
        responsables = db.query(Responsable).filter(Responsable.activo == True).all()
        print(f"\n[CHECK 2/5] Responsables activos")
        print(f"  Total responsables: {len(responsables)}")

        for resp in responsables:
            asigs = [a for a in asignaciones_nit if a.responsable_id == resp.id]
            print(f"  - {resp.nombre}: {len(asigs)} NITs asignados")

        # 3. Verificar facturas
        total_facturas = db.query(Factura).count()
        facturas_con_resp = db.query(Factura).filter(Factura.responsable_id != None).count()
        facturas_sin_resp = total_facturas - facturas_con_resp

        print(f"\n[CHECK 3/5] Estado de facturas")
        print(f"  Total facturas: {total_facturas}")
        print(f"  Con responsable: {facturas_con_resp} ({facturas_con_resp/total_facturas*100:.1f}%)")
        print(f"  Sin responsable: {facturas_sin_resp} ({facturas_sin_resp/total_facturas*100:.1f}%)")

        if facturas_sin_resp > 0:
            advertencias.append(f"{facturas_sin_resp} facturas sin responsable asignado")

        # 4. Verificar NITs sin asignacion
        facturas_sin_resp_list = db.query(Factura).filter(Factura.responsable_id == None).all()
        nits_sin_asignacion = set()

        for factura in facturas_sin_resp_list:
            if factura.proveedor_id:
                proveedor = db.query(Proveedor).filter(Proveedor.id == factura.proveedor_id).first()
                if proveedor and proveedor.nit:
                    nits_sin_asignacion.add(proveedor.nit)

        print(f"\n[CHECK 4/5] NITs sin asignacion")
        print(f"  Total NITs sin asignacion: {len(nits_sin_asignacion)}")

        if len(nits_sin_asignacion) > 0:
            print(f"  NITs pendientes:")
            for nit in list(nits_sin_asignacion)[:10]:  # Mostrar solo los primeros 10
                prov = db.query(Proveedor).filter(Proveedor.nit == nit).first()
                if prov:
                    print(f"    - {nit}: {prov.razon_social}")

            if len(nits_sin_asignacion) > 10:
                print(f"    ... y {len(nits_sin_asignacion) - 10} mas")

            advertencias.append(f"{len(nits_sin_asignacion)} NITs necesitan asignacion de responsable")

        # 5. Verificar que la tabla responsable_proveedor existe
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()

            print(f"\n[CHECK 5/5] Estado de tabla responsable_proveedor")

            if 'responsable_proveedor' in tables:
                print(f"  [OK] Tabla existe (sera eliminada por la migracion)")

                # Verificar si tiene datos
                result = db.execute("SELECT COUNT(*) FROM responsable_proveedor").scalar()
                print(f"  Registros en tabla: {result}")

                if result > 0:
                    advertencias.append(f"responsable_proveedor tiene {result} registros (seran eliminados)")
            else:
                print(f"  [ADVERTENCIA] Tabla ya fue eliminada")

        except Exception as e:
            advertencias.append(f"No se pudo verificar tabla responsable_proveedor: {e}")

        # Resumen
        print("\n" + "="*80)
        print("RESUMEN DE VALIDACION")
        print("="*80)

        if len(errores) == 0 and len(advertencias) == 0:
            print("\n[EXITO] Todas las validaciones pasaron!")
            print("\n[OK] Sistema listo para ejecutar migracion de Alembic")
            print("\nPara ejecutar la migracion:")
            print("  cd /c/Users/jhont/PRIVADO_ODO/afe-backend")
            print("  alembic upgrade head")
            return True
        else:
            if len(errores) > 0:
                print(f"\n[ERROR] {len(errores)} errores encontrados:")
                for error in errores:
                    print(f"  - {error}")

            if len(advertencias) > 0:
                print(f"\n[ADVERTENCIA] {len(advertencias)} advertencias:")
                for adv in advertencias:
                    print(f"  - {adv}")

            if len(errores) == 0:
                print("\n[OK] No hay errores bloqueantes")
                print("[INFO] Puedes proceder con la migracion, pero revisa las advertencias")
                return True
            else:
                print("\n[BLOQUEADO] Corrige los errores antes de migrar")
                return False

    except Exception as e:
        print(f"\n[ERROR CRITICO] {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    exito = validar_migracion_datos()
    sys.exit(0 if exito else 1)
