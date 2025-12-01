#!/usr/bin/env python3
"""
Script para sincronizar los workflows con usuarios que realmente existen.

Los workflows tienen responsable_id = 1, 2, 3 pero esos usuarios no existen.
Este script reemplaza esos IDs con un usuario válido que sí existe.
"""

import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import func
from app.db.session import SessionLocal
from app.models.workflow_aprobacion import WorkflowAprobacionFactura
from app.models.usuario import Usuario
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Sincroniza workflows con usuarios válidos."""
    logger.info("="*100)
    logger.info("SINCRONIZACIÓN DE WORKFLOWS CON USUARIOS VÁLIDOS")
    logger.info("="*100)

    db = SessionLocal()

    try:
        # 1. Ver distribución actual
        logger.info("\n1. DISTRIBUCIÓN ACTUAL DE responsable_id:")
        result = db.query(
            WorkflowAprobacionFactura.responsable_id,
            func.count(WorkflowAprobacionFactura.id).label('count')
        ).group_by(WorkflowAprobacionFactura.responsable_id).all()

        for responsable_id, count in result:
            print(f"   responsable_id={responsable_id}: {count} workflows")

        # 2. Listar usuarios válidos
        logger.info("\n2. USUARIOS VÁLIDOS QUE EXISTEN:")
        usuarios = db.query(Usuario).filter(Usuario.activo == True).all()
        for u in usuarios:
            print(f"   ID: {u.id}, usuario: {u.usuario}, nombre: {u.nombre}, email: {u.email}")

        # 3. Seleccionar usuario destino
        logger.info("\n3. SELECCIONAR USUARIO DESTINO:")
        usuario_destino_id = 6  # john.taimalp
        usuario = db.query(Usuario).filter(Usuario.id == usuario_destino_id).first()
        if not usuario:
            logger.error(f"❌ Usuario con ID {usuario_destino_id} no existe")
            return

        logger.info(f"   Usuario destino: ID {usuario.id} - {usuario.usuario} ({usuario.nombre})")
        logger.info(f"   Email: {usuario.email}")

        # 4. Actualizar workflows con IDs inválidos (1, 2, 3)
        logger.info(f"\n4. ACTUALIZANDO WORKFLOWS:")
        workflows_actualizados = db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.responsable_id.in_([1, 2, 3, None])
        ).all()

        logger.info(f"   Total de workflows a actualizar: {len(workflows_actualizados)}")

        if len(workflows_actualizados) > 0:
            logger.info(f"\n   Primeros 5 workflows a actualizar:")
            for wf in workflows_actualizados[:5]:
                logger.info(
                    f"     - Factura ID: {wf.factura_id}, "
                    f"responsable_id: {wf.responsable_id} → {usuario_destino_id}"
                )

            if len(workflows_actualizados) > 5:
                logger.info(f"   ... y {len(workflows_actualizados) - 5} más")

            # Confirmar antes de actualizar
            logger.info("\n" + "="*100)
            respuesta = input("¿Deseas continuar con la sincronización? (s/n): ").strip().lower()

            if respuesta != 's':
                logger.warning("Operación cancelada por el usuario.")
                return

            # Realizar actualización
            logger.info("\n5. REALIZANDO ACTUALIZACIÓN:")
            for wf in workflows_actualizados:
                wf.responsable_id = usuario_destino_id

            db.commit()
            logger.info(f"   ✅ {len(workflows_actualizados)} workflows actualizados exitosamente")

            # 6. Verificar resultado
            logger.info("\n6. VERIFICACIÓN POST-ACTUALIZACIÓN:")
            result = db.query(
                WorkflowAprobacionFactura.responsable_id,
                func.count(WorkflowAprobacionFactura.id).label('count')
            ).group_by(WorkflowAprobacionFactura.responsable_id).all()

            for responsable_id, count in result:
                print(f"   responsable_id={responsable_id}: {count} workflows")

            logger.info("\n" + "="*100)
            logger.info("✅ SINCRONIZACIÓN COMPLETADA")
            logger.info("="*100)
        else:
            logger.info("   ✅ No hay workflows con IDs inválidos. Sistema está sincronizado.")

    except Exception as e:
        logger.error(f"❌ Error durante sincronización: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
