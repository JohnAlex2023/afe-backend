"""
Script de prueba para verificar que el schema FacturaRead
esta poblando correctamente los campos calculados
"""
import sys
import os
# Fix para Windows encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.factura import Factura
from app.schemas.factura import FacturaRead
from sqlalchemy.orm import joinedload

def test_schema_population():
    """Prueba que el schema esta poblando correctamente los campos"""
    db: Session = SessionLocal()

    try:
        # Obtener una factura con relaciones cargadas
        factura = db.query(Factura).options(
            joinedload(Factura.proveedor),
            joinedload(Factura.responsable)
        ).first()

        if not factura:
            print("[ERROR] No se encontraron facturas en la BD")
            return

        print(f"\n[OK] Factura encontrada: {factura.numero_factura}")
        print(f"   ID: {factura.id}")
        print(f"   Estado: {factura.estado}")

        # Verificar relaciones
        print(f"\n[PROVEEDOR] Cargado: {factura.proveedor is not None}")
        if factura.proveedor:
            print(f"   NIT: {factura.proveedor.nit}")
            print(f"   Razon Social: {factura.proveedor.razon_social}")

        print(f"\n[RESPONSABLE] Cargado: {factura.responsable is not None}")
        if factura.responsable:
            print(f"   ID: {factura.responsable.id}")
            print(f"   Nombre: {factura.responsable.nombre}")
            print(f"   Usuario: {factura.responsable.usuario}")

        # Verificar campos de aprobacion/rechazo
        print(f"\n[AUDITORIA] Campos de auditoria:")
        print(f"   aprobado_por: {factura.aprobado_por}")
        print(f"   rechazado_por: {factura.rechazado_por}")
        print(f"   fecha_aprobacion: {factura.fecha_aprobacion}")
        print(f"   fecha_rechazo: {factura.fecha_rechazo}")

        # Convertir a schema
        print("\n[SCHEMA] Convirtiendo a FacturaRead schema...")
        factura_schema = FacturaRead.model_validate(factura)

        # Verificar campos calculados
        print(f"\n[CALCULADOS] Campos calculados en el schema:")
        print(f"   nit_emisor: {factura_schema.nit_emisor}")
        print(f"   nombre_emisor: {factura_schema.nombre_emisor}")
        print(f"   nombre_responsable: {factura_schema.nombre_responsable}")
        print(f"   accion_por: {factura_schema.accion_por}")
        print(f"   fecha_accion: {factura_schema.fecha_accion}")

        # Convertir a dict para ver JSON
        print(f"\n[JSON] JSON resultante:")
        factura_dict = factura_schema.model_dump()
        print(f"   nombre_responsable: {factura_dict.get('nombre_responsable')}")
        print(f"   accion_por: {factura_dict.get('accion_por')}")

        # Probar con varias facturas
        print("\n\n[TEST] Probando con las primeras 5 facturas:")
        facturas = db.query(Factura).options(
            joinedload(Factura.proveedor),
            joinedload(Factura.responsable)
        ).limit(5).all()

        for f in facturas:
            schema = FacturaRead.model_validate(f)
            print(f"\n   Factura {f.numero_factura}:")
            print(f"      Estado: {f.estado}")
            print(f"      Responsable DB: {f.responsable.nombre if f.responsable else 'None'}")
            print(f"      nombre_responsable: {schema.nombre_responsable}")
            print(f"      aprobado_por DB: {f.aprobado_por}")
            print(f"      accion_por: {schema.accion_por}")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_schema_population()
