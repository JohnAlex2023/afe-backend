"""Script simplificado para verificar duplicados en asignaciones"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from app.db.session import get_db

db = next(get_db())

print("=" * 80)
print("DIAGNOSTICO: Asignaciones ACTIVAS vs INACTIVAS")
print("=" * 80)

# Total de registros
result = db.execute(text("SELECT COUNT(*) as total FROM asignacion_nit_responsable"))
total = result.fetchone()[0]

# Activos
result = db.execute(text("SELECT COUNT(*) as activos FROM asignacion_nit_responsable WHERE activo = 1"))
activos = result.fetchone()[0]

# Inactivos
result = db.execute(text("SELECT COUNT(*) as inactivos FROM asignacion_nit_responsable WHERE activo = 0"))
inactivos = result.fetchone()[0]

print(f"Total registros: {total}")
print(f"Activos: {activos}")
print(f"Inactivos (soft delete): {inactivos}")
print()

# Verificar duplicados
result = db.execute(text("""
    SELECT nit, responsable_id, COUNT(*) as count,
           SUM(CASE WHEN activo = 1 THEN 1 ELSE 0 END) as activos,
           SUM(CASE WHEN activo = 0 THEN 1 ELSE 0 END) as inactivos
    FROM asignacion_nit_responsable
    GROUP BY nit, responsable_id
    HAVING COUNT(*) > 1
"""))

duplicados = list(result)

print("=" * 80)
print("DUPLICADOS (NIT + RESPONSABLE_ID):")
print("=" * 80)

if duplicados:
    print(f"Se encontraron {len(duplicados)} casos con duplicados:")
    for row in duplicados:
        print(f"  NIT: {row[0]} | Responsable: {row[1]} | Total: {row[2]} (Activos: {row[3]}, Inactivos: {row[4]})")
else:
    print("No se encontraron duplicados")

print()
print("=" * 80)
print("PROBLEMA IDENTIFICADO:")
print("=" * 80)
print(f"Hay {inactivos} registros marcados como 'activo=0' (soft delete)")
print("Estos registros NO se estan eliminando fisicamente de la base de datos.")
print("El frontend NO esta filtrando por 'activo=1', por lo que ve TODOS los registros.")
print("=" * 80)

db.close()
