"""
Script para verificar sincronizacion entre asignaciones y facturas
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Factura, AsignacionNitResponsable, Proveedor

def main():
    db = SessionLocal()
    try:
        # Verificar asignaciones activas
        asignaciones_activas = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == True
        ).all()

        print(f"\n=== ESTADO ACTUAL ===")
        print(f"Asignaciones ACTIVAS: {len(asignaciones_activas)}")

        # Verificar facturas con responsable_id
        facturas_con_responsable = db.query(Factura).filter(
            Factura.responsable_id.isnot(None)
        ).all()

        print(f"Facturas CON responsable_id: {len(facturas_con_responsable)}")

        # Mostrar detalle por responsable
        if facturas_con_responsable:
            print("\n=== FACTURAS POR RESPONSABLE ===")
            from collections import Counter
            responsables_count = Counter(f.responsable_id for f in facturas_con_responsable)
            for resp_id, count in responsables_count.items():
                print(f"  Responsable ID {resp_id}: {count} facturas")

        # Verificar inconsistencias
        print("\n=== VERIFICACION DE CONSISTENCIA ===")
        if len(asignaciones_activas) == 0 and len(facturas_con_responsable) > 0:
            print("INCONSISTENCIA CRITICA!")
            print(f"  - 0 asignaciones activas")
            print(f"  - {len(facturas_con_responsable)} facturas con responsable_id asignado")
            print("  - Las facturas deberian tener responsable_id = NULL")

            # Mostrar algunas facturas afectadas
            print("\n=== PRIMERAS 5 FACTURAS AFECTADAS ===")
            for factura in facturas_con_responsable[:5]:
                proveedor = db.query(Proveedor).filter(Proveedor.id == factura.proveedor_id).first()
                print(f"  Factura #{factura.numero_factura}")
                print(f"    - Proveedor: {proveedor.nombre if proveedor else 'N/A'}")
                print(f"    - NIT: {proveedor.nit if proveedor else 'N/A'}")
                print(f"    - Responsable ID: {factura.responsable_id}")
                print(f"    - Estado: {factura.estado}")
        else:
            print("Sistema SINCRONIZADO correctamente")

    finally:
        db.close()

if __name__ == "__main__":
    main()
