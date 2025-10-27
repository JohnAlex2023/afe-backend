"""
Script para limpiar registros de asignacion_nit_responsable con activo=FALSE

Este script elimina TODOS los registros soft-deleted (activo=FALSE) de la BD.
Se ejecuta una sola vez para limpiar datos históricos antes del hard delete pattern.

ADVERTENCIA: Esta operación es irreversible. Backup antes de ejecutar.
"""

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.utils.logger import logger

def limpiar_asignaciones_inactivas():
    """
    Elimina todos los registros con activo=FALSE de la base de datos.
    """
    db: Session = SessionLocal()
    
    try:
        # Contar registros a eliminar
        total_inactivos = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == False
        ).count()
        
        if total_inactivos == 0:
            logger.info("No hay registros inactivos para limpiar. BD limpia.")
            return
        
        logger.warning(f"⚠️  Se van a eliminar {total_inactivos} registros con activo=FALSE")
        
        # Solicitar confirmación
        confirmacion = input(f"\n¿Deseas eliminar {total_inactivos} registros inactivos? (si/no): ").strip().lower()
        
        if confirmacion != 'si':
            logger.info("Operación cancelada.")
            return
        
        # Obtener registros a eliminar (para logging)
        registros_a_eliminar = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == False
        ).all()
        
        for asig in registros_a_eliminar:
            logger.info(f"Eliminando: NIT={asig.nit}, Responsable={asig.responsable_id}, ID={asig.id}")
        
        # Eliminar registros
        db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == False
        ).delete()
        
        db.commit()
        
        logger.info(f"✅ {total_inactivos} registros eliminados exitosamente")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error al limpiar registros: {str(e)}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    limpiar_asignaciones_inactivas()
