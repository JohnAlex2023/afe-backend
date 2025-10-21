"""Script para verificar el flujo completo de eliminación de asignaciones"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from app.db.session import get_db

# Test: verificar qué pasa con las asignaciones marcadas como inactivas
db = next(get_db())

print("=" * 80)
print("DIAGNÓSTICO: SISTEMA DE ASIGNACIONES NIT-RESPONSABLE")
print("=" * 80)

# 1. Verificar asignaciones totales
result = db.execute(text("SELECT COUNT(*) as total FROM asignacion_nit_responsable"))
total = result.fetchone()[0]
print(f"\n1. Total de asignaciones en base de datos: {total}")

# 2. Verificar asignaciones activas
result = db.execute(text("SELECT COUNT(*) as activos FROM asignacion_nit_responsable WHERE activo = 1"))
activos = result.fetchone()[0]
print(f"2. Asignaciones ACTIVAS: {activos}")

# 3. Verificar asignaciones inactivas
result = db.execute(text("SELECT COUNT(*) as inactivos FROM asignacion_nit_responsable WHERE activo = 0"))
inactivos = result.fetchone()[0]
print(f"3. Asignaciones INACTIVAS (soft delete): {inactivos}")

# 4. Mostrar las asignaciones inactivas (posibles residuos)
if inactivos > 0:
    print("\n" + "=" * 80)
    print("ASIGNACIONES INACTIVAS (POSIBLES RESIDUOS):")
    print("=" * 80)
    result = db.execute(text("""
        SELECT id, nit, nombre_proveedor, responsable_id, activo, creado_en, actualizado_en
        FROM asignacion_nit_responsable
        WHERE activo = 0
        ORDER BY actualizado_en DESC
        LIMIT 20
    """))

    for row in result:
        print(f"\nID: {row[0]}")
        print(f"  NIT: {row[1]}")
        print(f"  Proveedor: {row[2]}")
        print(f"  Responsable ID: {row[3]}")
        print(f"  Activo: {row[4]}")
        print(f"  Creado: {row[5]}")
        print(f"  Actualizado: {row[6]}")

# 5. Verificar duplicados potenciales (mismo NIT + mismo responsable_id)
print("\n" + "=" * 80)
print("VERIFICANDO DUPLICADOS (NIT + RESPONSABLE_ID):")
print("=" * 80)

result = db.execute(text("""
    SELECT nit, responsable_id, COUNT(*) as duplicados,
           SUM(CASE WHEN activo = 1 THEN 1 ELSE 0 END) as activos,
           SUM(CASE WHEN activo = 0 THEN 1 ELSE 0 END) as inactivos
    FROM asignacion_nit_responsable
    GROUP BY nit, responsable_id
    HAVING COUNT(*) > 1
    ORDER BY duplicados DESC
"""))

duplicados = list(result)
if duplicados:
    print(f"Se encontraron {len(duplicados)} casos con duplicados:")
    for row in duplicados:
        print(f"\n  NIT: {row[0]} | Responsable: {row[1]}")
        print(f"    Total registros: {row[2]} (Activos: {row[3]}, Inactivos: {row[4]})")
        print(f"     PROBLEMA: Violación del constraint UNIQUE si ambos están activos")
else:
    print("  No se encontraron duplicados (NIT + responsable_id)")

# 6. Verificar si hay asignaciones con mismo NIT a diferentes responsables
print("\n" + "=" * 80)
print("VERIFICANDO NITs ASIGNADOS A MÚLTIPLES RESPONSABLES:")
print("=" * 80)

result = db.execute(text("""
    SELECT nit, COUNT(DISTINCT responsable_id) as num_responsables,
           GROUP_CONCAT(DISTINCT responsable_id ORDER BY responsable_id) as responsables
    FROM asignacion_nit_responsable
    WHERE activo = 1
    GROUP BY nit
    HAVING COUNT(DISTINCT responsable_id) > 1
    ORDER BY num_responsables DESC
"""))

multiples = list(result)
if multiples:
    print(f"  Se encontraron {len(multiples)} NITs con múltiples responsables (esto es válido):")
    for i, row in enumerate(multiples[:10], 1):
        print(f"  {i}. NIT: {row[0]} → {row[1]} responsables (IDs: {row[2]})")
else:
    print("No hay NITs asignados a múltiples responsables")

# 7. Verificar integridad referencial
print("\n" + "=" * 80)
print("VERIFICANDO INTEGRIDAD REFERENCIAL:")
print("=" * 80)

result = db.execute(text("""
    SELECT COUNT(*) as huerfanos
    FROM asignacion_nit_responsable a
    LEFT JOIN responsables r ON a.responsable_id = r.id
    WHERE r.id IS NULL
"""))
huerfanos = result.fetchone()[0]

if huerfanos > 0:
    print(f" PROBLEMA: {huerfanos} asignaciones con responsable_id inexistente")
else:
    print("  Todas las asignaciones tienen responsables válidos")

print("\n" + "=" * 80)
print("RESUMEN DEL DIAGNÓSTICO:")
print("=" * 80)
print(f"Total registros: {total}")
print(f"Activos: {activos}")
print(f"Inactivos (soft delete): {inactivos}")
print(f"Duplicados: {len(duplicados) if duplicados else 0}")
print(f"NITs con múltiples responsables: {len(multiples) if multiples else 0}")
print(f"Registros huérfanos: {huerfanos}")
print("=" * 80)

db.close()
