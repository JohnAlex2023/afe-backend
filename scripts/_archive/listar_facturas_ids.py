# -*- coding: utf-8 -*-
"""
Script para listar IDs de facturas con sus números.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

def main():
    from app.db.session import SessionLocal
    from app.models.factura import Factura, EstadoFactura

    db = SessionLocal()

    try:
        print("\n" + "=" * 100)
        print("FACTURAS EN REVISION O PENDIENTES")
        print("=" * 100)
        print(f"{'ID':^8} | {'Numero Factura':^20} | {'Proveedor':^30} | {'Estado':^20} | {'Responsable':^20}")
        print("-" * 100)

        facturas = db.query(Factura).filter(
            Factura.estado.in_([EstadoFactura.en_revision, EstadoFactura.pendiente])
        ).limit(20).all()

        for f in facturas:
            proveedor = f.proveedor.razon_social[:28] if f.proveedor else "Sin proveedor"
            responsable = f.responsable.usuario if f.responsable else "Sin responsable"

            print(f"{f.id:^8} | {f.numero_factura:^20} | {proveedor:^30} | {f.estado.value:^20} | {responsable:^20}")

        print("-" * 100)
        print(f"\nTotal: {len(facturas)} facturas")
        print("\nPara debuggear una factura, usa:")
        print("  python scripts/debug_factura_email.py")
        print("  E ingresa uno de los IDs de arriba\n")

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
