"""Limpiar estado parcial de migración Fase 2.5."""
import sys
sys.path.insert(0, '.')

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("Limpiando estado parcial de migración Fase 2.5...")

try:
    # 1. Eliminar constraint de facturas si existe
    try:
        db.execute(text('ALTER TABLE facturas DROP CONSTRAINT chk_facturas_total_coherente'))
        print("[OK] Constraint chk_facturas_total_coherente eliminado")
    except:
        print("[SKIP] Constraint chk_facturas_total_coherente no existe")

    # 2. Eliminar columna de validación si existe
    try:
        db.execute(text('ALTER TABLE facturas DROP COLUMN total_calculado_validacion'))
        print("[OK] Columna total_calculado_validacion eliminada")
    except:
        print("[SKIP] Columna total_calculado_validacion no existe")

    db.commit()
    print("\n[OK] Limpieza completada - Base de datos lista para migración limpia")

except Exception as e:
    print(f"\n[ERROR] {e}")
    db.rollback()
finally:
    db.close()
