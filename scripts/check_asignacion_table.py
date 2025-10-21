"""Script para verificar la estructura de la tabla asignacion_nit_responsable"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from app.db.session import engine

with engine.connect() as conn:
    result = conn.execute(text('SHOW CREATE TABLE asignacion_nit_responsable'))
    print(result.fetchone()[1])
