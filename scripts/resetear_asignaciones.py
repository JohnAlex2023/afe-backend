"""
Script para limpiar y reiniciar la tabla asignacion_nit_responsable

Este script:
1. Elimina TODOS los registros de asignacion_nit_responsable
2. Reinicia el auto-increment al valor inicial (1)
3. Verifica que la tabla esté limpia

ADVERTENCIA: Esta operación es IRREVERSIBLE
Hacer backup antes de ejecutar
"""

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.utils.logger import logger


def limpiar_asignaciones():
    """
    Elimina todos los registros de asignacion_nit_responsable y reinicia los IDs.
    """
    db: Session = SessionLocal()

    try:
        # PASO 1: Contar registros antes
        resultado_antes = db.execute(
            text("SELECT COUNT(*) as total FROM bd_afe.asignacion_nit_responsable")
        ).scalar()

        logger.warning(f"[WARN] Registros antes de limpieza: {resultado_antes}")

        # PASO 2: Solicitar confirmación
        confirmacion = input(
            f"\n[WARN] Se van a ELIMINAR {resultado_antes} registros de asignacion_nit_responsable\n"
            f"[WARN] Esta operacion es IRREVERSIBLE\n"
            f"[WARN] Escribe 'si' para confirmar: "
        ).strip().lower()

        if confirmacion != 'si':
            logger.info("[INFO] Operacion cancelada por el usuario")
            return False

        # PASO 3: Eliminar todos los registros
        logger.warning("[WARN] Eliminando registros...")
        db.execute(text("DELETE FROM bd_afe.asignacion_nit_responsable"))

        # PASO 4: Reiniciar auto-increment
        logger.warning("[WARN] Reiniciando auto-increment...")
        db.execute(text("ALTER TABLE bd_afe.asignacion_nit_responsable AUTO_INCREMENT = 1"))

        # PASO 5: Commit
        db.commit()

        # PASO 6: Verificar
        resultado_despues = db.execute(
            text("SELECT COUNT(*) as total FROM bd_afe.asignacion_nit_responsable")
        ).scalar()

        logger.info(f"[OK] Registros despues de limpieza: {resultado_despues}")
        logger.info("[OK] Auto-increment reiniciado a 1")
        logger.info("[OK] Tabla asignacion_nit_responsable limpia y lista")

        return True

    except Exception as e:
        db.rollback()
        logger.error(f"[ERROR] Error al limpiar tabla: {str(e)}", exc_info=True)
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("LIMPIAR TABLA: asignacion_nit_responsable")
    print("=" * 60)

    exito = limpiar_asignaciones()

    if exito:
        print("\n" + "=" * 60)
        print("[OK] TABLA LIMPIA EXITOSAMENTE")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[ERROR] ERROR AL LIMPIAR TABLA")
        print("=" * 60)
