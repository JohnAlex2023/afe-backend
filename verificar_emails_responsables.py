#!/usr/bin/env python3
"""
Script para verificar que los responsables tienen emails configurados.

Revisa todas las facturas y sus flujos de aprobación para asegurarse
de que los usuarios que aprobaron facturas tienen email configurado.
"""

import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session, joinedload
from app.db.session import SessionLocal
from app.models.factura import Factura, EstadoFactura
from app.models.workflow_aprobacion import WorkflowAprobacionFactura
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verificar_emails_responsables():
    """
    Verifica que todos los responsables tienen email configurado.
    """
    logger.info("="*100)
    logger.info("VERIFICACIÓN DE EMAILS DE RESPONSABLES")
    logger.info("="*100)

    db = SessionLocal()

    try:
        # Obtener todas las facturas en estado aprobada/aprobada_auto
        facturas = db.query(Factura).filter(
            Factura.estado.in_([
                EstadoFactura.aprobada.value,
                EstadoFactura.aprobada_auto.value,
                EstadoFactura.validada_contabilidad.value,
                EstadoFactura.devuelta_contabilidad.value
            ])
        ).all()

        logger.info(f"Total de facturas aprobadas: {len(facturas)}")
        logger.info("="*100)

        sin_responsable = 0
        sin_email = 0
        con_email = 0
        facturas_verificadas = []

        for factura in facturas:
            # Obtener el workflow de aprobación
            workflow = (
                db.query(WorkflowAprobacionFactura)
                .options(joinedload(WorkflowAprobacionFactura.usuario))
                .filter(WorkflowAprobacionFactura.factura_id == factura.id)
                .first()
            )

            if not workflow:
                logger.warning(
                    f"❌ Factura {factura.numero_factura} (ID: {factura.id}) - "
                    f"NO TIENE WORKFLOW DE APROBACIÓN"
                )
                sin_responsable += 1
                continue

            if not workflow.usuario:
                logger.warning(
                    f"❌ Factura {factura.numero_factura} (ID: {factura.id}) - "
                    f"Workflow sin usuario asociado"
                )
                sin_responsable += 1
                continue

            usuario = workflow.usuario

            if not usuario.email:
                logger.warning(
                    f"❌ Factura {factura.numero_factura} (ID: {factura.id}) - "
                    f"Usuario '{usuario.usuario}' SIN EMAIL configurado"
                )
                sin_email += 1
            else:
                logger.info(
                    f"✅ Factura {factura.numero_factura} (ID: {factura.id}) - "
                    f"Usuario: {usuario.usuario} ({usuario.nombre}) - "
                    f"Email: {usuario.email}"
                )
                con_email += 1
                facturas_verificadas.append({
                    'numero_factura': factura.numero_factura,
                    'usuario': usuario.usuario,
                    'nombre': usuario.nombre,
                    'email': usuario.email
                })

        logger.info("="*100)
        logger.info(f"RESUMEN:")
        logger.info(f"  - Facturas con responsable Y email: {con_email}")
        logger.info(f"  - Facturas sin responsable: {sin_responsable}")
        logger.info(f"  - Facturas con responsable pero SIN email: {sin_email}")
        logger.info("="*100)

        if sin_email > 0 or sin_responsable > 0:
            logger.error("⚠️  PROBLEMA DETECTADO:")
            if sin_responsable > 0:
                logger.error(f"   - {sin_responsable} facturas no tienen workflow de aprobación")
            if sin_email > 0:
                logger.error(f"   - {sin_email} facturas tienen responsable pero sin email")
            logger.error("   Estos usuarios no recibirán emails de devolución")

    finally:
        db.close()


if __name__ == "__main__":
    verificar_emails_responsables()
