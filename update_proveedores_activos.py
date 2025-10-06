"""
Script para activar todos los proveedores existentes en la base de datos.
"""
from app.core.database import SessionLocal
from app.models.proveedor import Proveedor

db = SessionLocal()

try:
    # Actualizar todos los proveedores a activo = True
    updated = db.query(Proveedor).update({Proveedor.activo: True})
    db.commit()

    print(f"✅ {updated} proveedores actualizados a activo = True")

    # Verificar
    proveedores = db.query(Proveedor).all()
    print(f"\nTotal de proveedores: {len(proveedores)}")
    for p in proveedores:
        print(f"  - {p.nit} | {p.razon_social} | Activo: {p.activo}")

except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
finally:
    db.close()
