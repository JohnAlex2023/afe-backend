"""
Script de prueba para verificar que ambos responsables se muestran correctamente
"""
import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from sqlalchemy.orm import Session, joinedload
from app.db.session import SessionLocal
from app.models.factura import Factura
from app.schemas.factura import FacturaRead

def test_ambos_responsables():
    """Prueba que ambos responsables se muestran en las facturas"""
    db: Session = SessionLocal()

    try:
        # Buscar facturas del responsable Alex (ID: 5)
        facturas_alex = db.query(Factura).options(
            joinedload(Factura.proveedor),
            joinedload(Factura.responsable)
        ).filter(Factura.responsable_id == 5).limit(3).all()

        print("[INFO] Facturas de Alex (ID: 5):")
        print("-" * 70)
        for f in facturas_alex:
            schema = FacturaRead.model_validate(f)
            print(f"  Factura: {f.numero_factura:20} | Responsable: {schema.nombre_responsable}")

        # Buscar facturas del responsable John (ID: 6)
        facturas_john = db.query(Factura).options(
            joinedload(Factura.proveedor),
            joinedload(Factura.responsable)
        ).filter(Factura.responsable_id == 6).limit(3).all()

        print(f"\n[INFO] Facturas de John (ID: 6):")
        print("-" * 70)
        for f in facturas_john:
            schema = FacturaRead.model_validate(f)
            print(f"  Factura: {f.numero_factura:20} | Responsable: {schema.nombre_responsable}")

        # Contar totales
        total_alex = db.query(Factura).filter(Factura.responsable_id == 5).count()
        total_john = db.query(Factura).filter(Factura.responsable_id == 6).count()
        total_sin_resp = db.query(Factura).filter(Factura.responsable_id == None).count()

        print(f"\n[RESUMEN]")
        print("-" * 70)
        print(f"  Total facturas Alex:         {total_alex}")
        print(f"  Total facturas John:         {total_john}")
        print(f"  Total sin responsable:       {total_sin_resp}")
        print(f"  Total con responsable:       {total_alex + total_john}")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    test_ambos_responsables()
