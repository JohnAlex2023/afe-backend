"""Script temporal para limpiar columnas de intento de migración fallido."""
import sys
sys.path.insert(0, '.')

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    # Intentar eliminar columna si existe
    db.execute(text('ALTER TABLE facturas DROP COLUMN total_calculado_validacion'))
    db.commit()
    print("Columna total_calculado_validacion eliminada")
except Exception as e:
    print(f"Columna no existe o ya fue eliminada: {e}")
    db.rollback()
finally:
    db.close()
