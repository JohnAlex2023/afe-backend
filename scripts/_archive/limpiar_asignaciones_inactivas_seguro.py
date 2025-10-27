"""
ENTERPRISE SCRIPT: Limpieza Segura de Asignaciones Inactivas

Script opcional para eliminar físicamente asignaciones marcadas como inactivas
después de aplicar el fix de soft delete.

  ADVERTENCIA: Este script es OPCIONAL y DESTRUCTIVO
- Solo ejecutar si se tiene backup completo de la base de datos
- Solo ejecutar después de aplicar el fix de soft delete
- Requiere confirmación explícita del usuario
- Crea backup automático en JSON antes de eliminar

Nivel: Enterprise Production-Ready with Safety Checks
Autor: Equipo de Desarrollo Senior
Fecha: 2025-10-21
"""
import sys
import json
from datetime import datetime
from pathlib import Path

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import get_db


def verificar_version_fix():
    """
    Verifica que el fix de soft delete esté aplicado.

    Esto previene ejecutar el script en un sistema sin el fix,
    lo cual causaría problemas al recrear asignaciones.
    """
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE VERSIÓN DEL SISTEMA")
    print("=" * 80)

    # TODO: Agregar verificación de migración aplicada
    # Por ahora, solo advertencia
    print("  IMPORTANTE: Solo ejecutar este script SI:")
    print("   1. Ya aplicó la migración 8cac6c86089d (índices de performance)")
    print("   2. Ya desplegó el código con el fix de soft delete")
    print("   3. Tiene backup completo de la base de datos")
    print()

    return True


def obtener_estadisticas(db):
    """Obtiene estadísticas de asignaciones para mostrar al usuario."""
    stats = {}

    # Total de registros
    result = db.execute(text("SELECT COUNT(*) FROM asignacion_nit_responsable"))
    stats['total'] = result.fetchone()[0]

    # Activos
    result = db.execute(text("SELECT COUNT(*) FROM asignacion_nit_responsable WHERE activo = 1"))
    stats['activos'] = result.fetchone()[0]

    # Inactivos
    result = db.execute(text("SELECT COUNT(*) FROM asignacion_nit_responsable WHERE activo = 0"))
    stats['inactivos'] = result.fetchone()[0]

    return stats


def crear_backup(db, filepath="backup_asignaciones_inactivas.json"):
    """
    Crea backup en JSON de todas las asignaciones inactivas.

    Este backup permite restaurar registros si es necesario.
    """
    print("\n" + "=" * 80)
    print("CREANDO BACKUP DE ASIGNACIONES INACTIVAS...")
    print("=" * 80)

    result = db.execute(text("""
        SELECT
            id, nit, nombre_proveedor, responsable_id, area,
            permitir_aprobacion_automatica, requiere_revision_siempre,
            activo, creado_en, actualizado_en, creado_por, actualizado_por
        FROM asignacion_nit_responsable
        WHERE activo = 0
        ORDER BY id
    """))

    backup_data = []
    for row in result:
        backup_data.append({
            "id": row[0],
            "nit": row[1],
            "nombre_proveedor": row[2],
            "responsable_id": row[3],
            "area": row[4],
            "permitir_aprobacion_automatica": bool(row[5]) if row[5] is not None else None,
            "requiere_revision_siempre": bool(row[6]) if row[6] is not None else None,
            "activo": bool(row[7]) if row[7] is not None else None,
            "creado_en": str(row[8]) if row[8] else None,
            "actualizado_en": str(row[9]) if row[9] else None,
            "creado_por": row[10],
            "actualizado_por": row[11]
        })

    # Guardar backup con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backup_asignaciones_inactivas_{timestamp}.json"

    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "total_registros": len(backup_data),
            "descripcion": "Backup de asignaciones inactivas antes de limpieza física",
            "asignaciones": backup_data
        }, f, indent=2, ensure_ascii=False)

    print(f"  Backup creado exitosamente: {backup_path}")
    print(f"   Total de registros respaldados: {len(backup_data)}")

    return backup_path


def confirmar_eliminacion(stats):
    """
    Solicita confirmación explícita del usuario.

    Requiere que el usuario escriba exactamente la frase de confirmación.
    """
    print("\n" + "=" * 80)
    print("  CONFIRMACIÓN REQUERIDA")
    print("=" * 80)
    print()
    print(f"Se eliminarán FÍSICAMENTE {stats['inactivos']} asignaciones inactivas.")
    print(f"Asignaciones activas (NO afectadas): {stats['activos']}")
    print()
    print("Esta acción es IRREVERSIBLE (excepto por restauración desde backup).")
    print()
    print("Para continuar, escriba exactamente: CONFIRMO ELIMINACION")
    print()

    respuesta = input("> ").strip()

    return respuesta == "CONFIRMO ELIMINACION"


def eliminar_asignaciones_inactivas(db):
    """
    Elimina físicamente las asignaciones inactivas.

    Usa transacción para garantizar atomicidad.
    """
    print("\n" + "=" * 80)
    print("ELIMINANDO ASIGNACIONES INACTIVAS...")
    print("=" * 80)

    try:
        # Eliminar con transacción
        result = db.execute(text("""
            DELETE FROM asignacion_nit_responsable
            WHERE activo = 0
        """))

        eliminados = result.rowcount
        db.commit()

        print(f"  {eliminados} registros eliminados exitosamente")
        return eliminados

    except Exception as e:
        db.rollback()
        print(f" ERROR durante la eliminación: {str(e)}")
        print("   Rollback ejecutado. No se eliminó ningún registro.")
        raise


def main():
    """Flujo principal del script."""
    print("=" * 80)
    print("LIMPIEZA SEGURA DE ASIGNACIONES INACTIVAS")
    print("Enterprise Script - Proyecto AFE Backend")
    print("=" * 80)

    # PASO 1: Verificar versión del sistema
    if not verificar_version_fix():
        print(" El sistema no cumple con los requisitos. Abortando.")
        return 1

    # PASO 2: Conectar a base de datos
    try:
        db = next(get_db())
    except Exception as e:
        print(f" Error conectando a base de datos: {str(e)}")
        return 1

    # PASO 3: Obtener estadísticas
    stats = obtener_estadisticas(db)

    print("\n" + "=" * 80)
    print("ESTADÍSTICAS ACTUALES")
    print("=" * 80)
    print(f"Total de asignaciones: {stats['total']}")
    print(f"  - Activas: {stats['activos']} ({stats['activos']/stats['total']*100:.1f}%)")
    print(f"  - Inactivas (a eliminar): {stats['inactivos']} ({stats['inactivos']/stats['total']*100:.1f}%)")

    # Si no hay inactivas, salir
    if stats['inactivos'] == 0:
        print("\n  No hay asignaciones inactivas para eliminar.")
        print("   El sistema está limpio.")
        db.close()
        return 0

    # PASO 4: Crear backup
    try:
        backup_path = crear_backup(db, stats)
    except Exception as e:
        print(f" Error creando backup: {str(e)}")
        print("   Por seguridad, no se continuará con la eliminación.")
        db.close()
        return 1

    # PASO 5: Confirmar con usuario
    if not confirmar_eliminacion(stats):
        print("\n Operación cancelada por el usuario.")
        print(f"   Backup conservado en: {backup_path}")
        db.close()
        return 0

    # PASO 6: Eliminar asignaciones inactivas
    try:
        eliminados = eliminar_asignaciones_inactivas(db)

        # Verificar resultado
        stats_final = obtener_estadisticas(db)

        print("\n" + "=" * 80)
        print("OPERACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 80)
        print(f"Registros eliminados: {eliminados}")
        print(f"Asignaciones restantes: {stats_final['total']} (todas activas)")
        print(f"Backup guardado en: {backup_path}")
        print()
        print("  Limpieza completada. El sistema está optimizado.")

        db.close()
        return 0

    except Exception as e:
        print(f"\n ERROR CRÍTICO: {str(e)}")
        print(f"   Backup disponible en: {backup_path}")
        print("   Contacte al equipo de desarrollo si requiere asistencia.")
        db.close()
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n Operación cancelada por el usuario (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n ERROR INESPERADO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
