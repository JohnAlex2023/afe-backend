#!/usr/bin/env python3
"""
Script para reparar workflows de aprobación que no tienen usuario_id.

Problema: Las facturas aprobadas no tienen el campo usuario_id asignado
en la tabla workflow_aprobacion_factura, lo que hace que no se puedan
enviar emails de devolución.

Solución: Asignar un usuario_id por defecto a todos los workflows sin usuario.
"""

import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import joinedload
from app.db.session import SessionLocal
from app.models.factura import Factura, EstadoFactura
from app.models.workflow_aprobacion import WorkflowAprobacionFactura
from app.models.usuario import Usuario
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def encontrar_usuarios_disponibles(db):
    """Encuentra usuarios disponibles que podrían ser responsables."""
    usuarios = db.query(Usuario).filter(
        Usuario.activo == True
    ).all()

    logger.info(f"Usuarios disponibles (activos con email):")
    usuarios_con_email = []
    for u in usuarios:
        if u.email:
            logger.info(f"  - ID: {u.id}, usuario: {u.usuario} ({u.nombre or 'Sin nombre'}) - Email: {u.email}")
            usuarios_con_email.append(u)

    return usuarios_con_email


def reparar_workflows():
    """
    Repara los workflows que no tienen usuario_id.
    """
    logger.info("="*100)
    logger.info("REPARACIÓN DE WORKFLOWS SIN USUARIO")
    logger.info("="*100)

    db = SessionLocal()

    try:
        # Obtener todas las facturas aprobadas
        facturas = db.query(Factura).filter(
            Factura.estado.in_([
                EstadoFactura.aprobada.value,
                EstadoFactura.aprobada_auto.value,
                EstadoFactura.validada_contabilidad.value,
                EstadoFactura.devuelta_contabilidad.value
            ])
        ).all()

        logger.info(f"Total de facturas aprobadas: {len(facturas)}")

        # Encontrar workflows sin usuario
        workflows_sin_usuario = 0
        workflows_con_usuario = 0
        workflows_reparados = 0

        for factura in facturas:
            workflow = (
                db.query(WorkflowAprobacionFactura)
                .options(joinedload(WorkflowAprobacionFactura.usuario))
                .filter(WorkflowAprobacionFactura.factura_id == factura.id)
                .first()
            )

            if not workflow:
                logger.warning(f"Factura {factura.numero_factura} (ID: {factura.id}) - SIN WORKFLOW")
                continue

            if workflow.usuario:
                workflows_con_usuario += 1
                continue

            workflows_sin_usuario += 1
            logger.warning(
                f"Factura {factura.numero_factura} (ID: {factura.id}) - "
                f"Workflow sin usuario. responsable_id={workflow.responsable_id}"
            )

        logger.info("="*100)
        logger.info("RESUMEN PRE-REPARACIÓN:")
        logger.info(f"  - Workflows con usuario: {workflows_con_usuario}")
        logger.info(f"  - Workflows sin usuario: {workflows_sin_usuario}")
        logger.info("="*100)

        if workflows_sin_usuario == 0:
            logger.info("✅ Todos los workflows tienen usuario. No hay nada que reparar.")
            return

        # Preguntar al usuario qué hacer
        logger.info("\n⚠️  OPCIÓN 1: Asignar un usuario por defecto a todos los workflows sin usuario")
        logger.info("⚠️  OPCIÓN 2: Cancelar y revisar manualmente")
        logger.info("\nPara usar este script, necesitas un usuario_id válido.")

        usuarios = encontrar_usuarios_disponibles(db)

        if not usuarios:
            logger.error("❌ No hay usuarios disponibles para asignar. Operación cancelada.")
            return

        logger.info("\n" + "="*100)
        logger.info("INSTRUCCIONES:")
        logger.info("1. Ejecutar este script con el usuario_id como parámetro")
        logger.info(f"   Ejemplo: python reparar_workflows_sin_usuario.py 1")
        logger.info("="*100)

    finally:
        db.close()


def reparar_con_usuario_id(usuario_id: int):
    """
    Asigna un usuario_id a todos los workflows sin usuario.

    Args:
        usuario_id: ID del usuario a asignar
    """
    logger.info("="*100)
    logger.info(f"REPARACIÓN CON USUARIO_ID={usuario_id}")
    logger.info("="*100)

    db = SessionLocal()

    try:
        # Verificar que el usuario existe
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:
            logger.error(f"❌ Usuario con ID {usuario_id} no existe")
            return

        logger.info(f"Usuario a asignar: {usuario.usuario} ({usuario.nombre or 'Sin nombre'}) - {usuario.email}")

        # Obtener workflows sin usuario
        workflows_sin_usuario = db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.responsable_id == None
        ).all()

        logger.info(f"\nTotal de workflows sin usuario: {len(workflows_sin_usuario)}")

        if len(workflows_sin_usuario) == 0:
            logger.info("✅ Todos los workflows tienen usuario. Nada que reparar.")
            return

        # Mostrar preview de cambios
        logger.info("\n" + "-"*100)
        logger.info("VISTA PREVIA DE CAMBIOS (primeros 5):")
        logger.info("-"*100)
        for workflow in workflows_sin_usuario[:5]:
            factura = workflow.factura
            logger.info(
                f"  Factura {factura.numero_factura} (ID: {factura.id}) "
                f"→ Asignar usuario_id={usuario_id}"
            )

        if len(workflows_sin_usuario) > 5:
            logger.info(f"  ... y {len(workflows_sin_usuario) - 5} más")

        # Confirmación
        logger.info("\n" + "="*100)
        respuesta = input("¿Deseas continuar con la reparación? (s/n): ").strip().lower()

        if respuesta != 's':
            logger.warning("Operación cancelada por el usuario.")
            return

        # Realizar la reparación
        logger.info("\n🔄 Reparando workflows...")
        for workflow in workflows_sin_usuario:
            workflow.responsable_id = usuario_id

        db.commit()

        logger.info(f"✅ {len(workflows_sin_usuario)} workflows han sido reparados correctamente")
        logger.info(f"   Usuario asignado: {usuario.usuario}")
        logger.info("="*100)

    except Exception as e:
        logger.error(f"❌ Error durante la reparación: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Sin argumentos: mostrar análisis
        reparar_workflows()
    elif len(sys.argv) == 2:
        # Con usuario_id: realizar reparación
        try:
            usuario_id = int(sys.argv[1])
            reparar_con_usuario_id(usuario_id)
        except ValueError:
            logger.error(f"❌ usuario_id debe ser un número entero. Recibido: {sys.argv[1]}")
    else:
        logger.error("Uso: python reparar_workflows_sin_usuario.py [usuario_id]")
