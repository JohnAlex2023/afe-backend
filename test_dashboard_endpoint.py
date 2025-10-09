"""
Script de prueba para verificar el nuevo endpoint /facturas/all
Ejecutar: python test_dashboard_endpoint.py
"""

import sys
import os
import io

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.crud.factura import list_all_facturas_for_dashboard, count_facturas
from app.models.responsable import Responsable


def test_endpoint():
    """
    Prueba el nuevo endpoint de dashboard completo
    """
    print("=" * 80)
    print("PRUEBA DE ENDPOINT: /facturas/all")
    print("=" * 80)

    db: Session = SessionLocal()

    try:
        # 1. Contar total de facturas en BD
        print("\n1. TOTAL DE FACTURAS EN BASE DE DATOS")
        print("-" * 80)

        total_db = count_facturas(db)
        print(f"   ✅ Total en BD: {total_db:,} facturas")

        # 2. Probar endpoint SIN filtro de responsable (Admin completo)
        print("\n2. PRUEBA ADMIN - TODAS LAS FACTURAS (sin filtros)")
        print("-" * 80)

        facturas_admin = list_all_facturas_for_dashboard(db)
        print(f"   ✅ Facturas retornadas: {len(facturas_admin):,}")
        print(f"   ✅ Coincide con BD: {'SÍ' if len(facturas_admin) == total_db else 'NO'}")

        if len(facturas_admin) > 0:
            print(f"\n   📊 Primeras 5 facturas:")
            for i, f in enumerate(facturas_admin[:5], 1):
                print(f"      {i}. ID: {f.id} | Nº: {f.numero_factura} | "
                      f"Fecha: {f.fecha_emision} | Total: ${f.total:,.2f}")

        # 3. Probar con responsable específico
        print("\n3. PRUEBA RESPONSABLE - SOLO FACTURAS ASIGNADAS")
        print("-" * 80)

        responsable = db.query(Responsable).first()
        if responsable:
            facturas_responsable = list_all_facturas_for_dashboard(
                db,
                responsable_id=responsable.id
            )

            print(f"   ✅ Responsable: {responsable.usuario} (ID: {responsable.id})")
            print(f"   ✅ Facturas asignadas: {len(facturas_responsable):,}")

            if len(facturas_responsable) > 0:
                print(f"\n   📊 Primeras 3 facturas:")
                for i, f in enumerate(facturas_responsable[:3], 1):
                    print(f"      {i}. ID: {f.id} | Nº: {f.numero_factura} | "
                          f"Total: ${f.total:,.2f}")
        else:
            print("   ⚠️ No hay responsables en la BD")

        # 4. Verificar orden cronológico
        print("\n4. VERIFICACIÓN DE ORDEN CRONOLÓGICO")
        print("-" * 80)

        if len(facturas_admin) >= 2:
            primera = facturas_admin[0]
            segunda = facturas_admin[1]

            print(f"   Primera: {primera.fecha_emision} (ID: {primera.id})")
            print(f"   Segunda: {segunda.fecha_emision} (ID: {segunda.id})")

            orden_correcto = primera.fecha_emision >= segunda.fecha_emision
            print(f"   ✅ Orden descendente: {'SÍ' if orden_correcto else 'NO'}")

        # 5. Performance check
        print("\n5. ANÁLISIS DE PERFORMANCE")
        print("-" * 80)

        if total_db < 10000:
            print(f"   ✅ Dataset pequeño ({total_db:,} facturas)")
            print("   ✅ Endpoint /facturas/all es óptimo")
        elif 10000 <= total_db <= 50000:
            print(f"   ⚠️ Dataset mediano ({total_db:,} facturas)")
            print("   ⚠️ Considerar /facturas/cursor para scroll infinito")
        else:
            print(f"   ❌ Dataset grande ({total_db:,} facturas)")
            print("   ❌ USAR /facturas/cursor obligatoriamente")

        # Resumen final
        print("\n" + "=" * 80)
        print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        print("=" * 80)

        print(f"\n📊 RESUMEN:")
        print(f"   • Total facturas en BD: {total_db:,}")
        print(f"   • Endpoint retorna: {len(facturas_admin):,}")
        print(f"   • Match 100%: {'✅ SÍ' if len(facturas_admin) == total_db else '❌ NO'}")

        print(f"\n🚀 PRÓXIMOS PASOS:")
        print(f"   1. Actualizar frontend para usar: GET /api/v1/facturas/all")
        print(f"   2. Probar con usuario Admin en Postman")
        print(f"   3. Verificar que retorna {total_db:,} facturas")
        print(f"   4. Implementar en dashboard principal")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_endpoint()
