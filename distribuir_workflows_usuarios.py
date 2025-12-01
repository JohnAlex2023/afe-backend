#!/usr/bin/env python3
"""
Script para distribuir los workflows entre los usuarios reales disponibles.

En lugar de asignar todos a un solo usuario (john.taimalp),
distribuimos equilibradamente entre todos los usuarios activos.
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
    """Distribuye workflows entre usuarios activos."""
    logger.info("="*100)
    logger.info("DISTRIBUCIÓN DE WORKFLOWS ENTRE USUARIOS ACTIVOS")
    logger.info("="*100)

    db = SessionLocal()

    try:
        # 1. Obtener todos los usuarios activos
        usuarios = db.query(Usuario).filter(Usuario.activo == True).all()

        logger.info("\n1. USUARIOS DISPONIBLES:")
        for u in usuarios:
            print(f"   ID: {u.id}, usuario: {u.usuario:20s} email: {u.email:40s}")

        # 2. Contar workflows actuales
        logger.info("\n2. DISTRIBUCIÓN ACTUAL DE WORKFLOWS:")
        result = db.query(
            WorkflowAprobacionFactura.responsable_id,
            func.count(WorkflowAprobacionFactura.id).label('count')
        ).group_by(WorkflowAprobacionFactura.responsable_id).order_by(
            WorkflowAprobacionFactura.responsable_id
        ).all()

        total_workflows = 0
        for responsable_id, count in result:
            usuario = db.query(Usuario).filter(Usuario.id == responsable_id).first()
            usuario_name = usuario.usuario if usuario else "DESCONOCIDO"
            print(f"   responsable_id={responsable_id} ({usuario_name:20s}): {count:4d} workflows")
            total_workflows += count

        logger.info(f"\n   Total de workflows: {total_workflows}")

        # 3. Distribuir
        logger.info(f"\n3. REDISTRIBUYENDO ENTRE {len(usuarios)} USUARIOS:")

        # Calcular workflows por usuario
        workflows_per_user = total_workflows // len(usuarios)
        remainder = total_workflows % len(usuarios)

        logger.info(f"   Workflows por usuario: {workflows_per_user}")
        logger.info(f"   Usuarios con 1 extra: {remainder}")

        # Mostrar cómo se distribuirá
        logger.info(f"\n   PLAN DE DISTRIBUCIÓN:")
        for i, usuario in enumerate(usuarios):
            count = workflows_per_user + (1 if i < remainder else 0)
            print(f"   - {usuario.usuario:20s} (ID: {usuario.id}): {count} workflows")

        # Confirmar antes de ejecutar
        logger.info("\n" + "="*100)
        respuesta = input("¿Deseas continuar con la redistribución? (s/n): ").strip().lower()

        if respuesta != 's':
            logger.warning("Operación cancelada por el usuario.")
            return

        # 4. Realizar redistribución
        logger.info("\n4. REALIZANDO REDISTRIBUCIÓN:")

        # Obtener todos los workflows ordenados por ID
        workflows = db.query(WorkflowAprobacionFactura).order_by(
            WorkflowAprobacionFactura.id
        ).all()

        # Distribuir índices de usuarios
        usuario_index = 0
        workflows_asignados_por_usuario = {u.id: 0 for u in usuarios}

        for i, workflow in enumerate(workflows):
            usuario = usuarios[usuario_index]
            workflow.responsable_id = usuario.id
            workflows_asignados_por_usuario[usuario.id] += 1

            # Pasar al siguiente usuario cuando haya asignado suficientes
            workflows_para_este = workflows_per_user + (1 if usuario_index < remainder else 0)
            if workflows_asignados_por_usuario[usuario.id] >= workflows_para_este:
                usuario_index += 1
                if usuario_index >= len(usuarios):
                    usuario_index = len(usuarios) - 1

        db.commit()
        logger.info(f"   ✅ {len(workflows)} workflows redistribuidos exitosamente")

        # 5. Verificar resultado
        logger.info("\n5. VERIFICACIÓN POST-DISTRIBUCIÓN:")
        result = db.query(
            WorkflowAprobacionFactura.responsable_id,
            func.count(WorkflowAprobacionFactura.id).label('count')
        ).group_by(WorkflowAprobacionFactura.responsable_id).order_by(
            WorkflowAprobacionFactura.responsable_id
        ).all()

        for responsable_id, count in result:
            usuario = db.query(Usuario).filter(Usuario.id == responsable_id).first()
            usuario_name = usuario.usuario if usuario else "DESCONOCIDO"
            print(f"   responsable_id={responsable_id} ({usuario_name:20s}): {count:4d} workflows")

        logger.info("\n" + "="*100)
        logger.info("✅ REDISTRIBUCIÓN COMPLETADA")
        logger.info("="*100)

    except Exception as e:
        logger.error(f"❌ Error durante distribución: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
