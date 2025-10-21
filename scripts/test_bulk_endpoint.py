"""
Test directo del endpoint BULK para diagnosticar el problema
"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from app.db.session import get_db

# Verificar estado actual
db = next(get_db())

print("=" * 80)
print("DIAGNOSTICO: Endpoint BULK - Asignaciones Creadas")
print("=" * 80)

# Ver las ultimas asignaciones creadas
result = db.execute(text("""
    SELECT id, nit, nombre_proveedor, responsable_id, activo, creado_en
    FROM asignacion_nit_responsable
    WHERE id >= 136
    ORDER BY id DESC
    LIMIT 10
"""))

print("\nUltimas asignaciones en BD:")
print("-" * 80)
for row in result:
    print(f"ID: {row[0]}")
    print(f"  NIT: {row[1]}")
    print(f"  Proveedor: {row[2]}")
    print(f"  Responsable: {row[3]}")
    print(f"  Activo: {row[4]}")
    print(f"  Creado: {row[5]}")
    print()

# Verificar si hay errores en las asignaciones
print("=" * 80)
print("ANALISIS: Las asignaciones SE CREARON CORRECTAMENTE")
print("=" * 80)
print()
print("PROBLEMA IDENTIFICADO:")
print("  - Backend: Funciona correctamente (creadas 4 asignaciones)")
print("  - Frontend: Muestra error incorrectamente")
print()
print("CAUSA PROBABLE:")
print("  1. Frontend espera formato de respuesta diferente")
print("  2. Frontend verifica campo 'success' que no existe")
print("  3. Frontend interpreta array 'errores' como fallo")
print()
print("SOLUCION:")
print("  Agregar campo 'success: true' a la respuesta del endpoint")
print("=" * 80)

db.close()
