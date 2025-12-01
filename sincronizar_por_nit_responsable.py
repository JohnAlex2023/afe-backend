#!/usr/bin/env python3
"""
Script para sincronizar workflows basado en el NIT del proveedor.

Para facturas aprobadas automáticamente "Sistema Automático":
1. Obtener el NIT del proveedor de la factura
2. Buscar en asignacion_nit_responsables quién es el responsable de ese NIT
3. Asignar el workflow a ese responsable
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


def main():
    """Sincroniza workflows basado en NIT responsables."""
    logger.info("="*100)
    logger.info("SINCRONIZACIÓN DE WORKFLOWS POR NIT RESPONSABLE")
    logger.info("="*100)

    db = SessionLocal()

    try:
        # 1. Listar tablas disponibles para entender la estructura
        logger.info("\n1. ANALIZANDO ESTRUCTURA DE ASIGNACIONES:")

        # Intentar obtener la tabla de asignaciones
        from sqlalchemy import inspect, text
        inspector = inspect(db.bind)
        tablas = inspector.get_table_names()

        logger.info(f"   Tablas en la BD: {tablas}")

        # Buscar tabla de asignaciones de NIT
        asignacion_table = None
        for tabla in tablas:
            if 'asignacion' in tabla.lower() and 'nit' in tabla.lower():
                asignacion_table = tabla
                logger.info(f"   ✅ Encontrada tabla: {tabla}")

                # Mostrar columnas
                columns = [c['name'] for c in inspector.get_columns(tabla)]
                logger.info(f"      Columnas: {columns}")

        if not asignacion_table:
            logger.warning("   ⚠️  No se encontró tabla de asignación de NIT")
            logger.info("\n   Buscando información en workflow_aprobacion_facturas...")

            # Ver qué campos tienen las facturas
            facturas_aprob_auto = db.query(Factura).filter(
                Factura.accion_por == "Sistema Automático"
            ).limit(5).all()

            for f in facturas_aprob_auto:
                logger.info(f"   Factura {f.numero_factura}: nit_proveedor={f.nit_proveedor if hasattr(f, 'nit_proveedor') else 'NO EXISTE'}")

            return

        # 2. Analizar facturas con "Sistema Automático"
        logger.info(f"\n2. FACTURAS CON APROBACIÓN AUTOMÁTICA:")

        facturas_auto = db.query(Factura).filter(
            Factura.accion_por == "Sistema Automático",
            Factura.estado.in_([
                EstadoFactura.aprobada.value,
                EstadoFactura.aprobada_auto.value,
                EstadoFactura.validada_contabilidad.value,
                EstadoFactura.devuelta_contabilidad.value
            ])
        ).all()

        logger.info(f"   Total: {len(facturas_auto)} facturas")

        # 3. Para cada factura, buscar responsable del NIT
        logger.info(f"\n3. BUSCANDO RESPONSABLES POR NIT:")

        cambios_pendientes = 0
        mapa_nit_responsables = {}

        for factura in facturas_auto[:10]:  # Ver primeras 10
            nit = factura.nit_proveedor if hasattr(factura, 'nit_proveedor') else None

            if not nit:
                logger.warning(f"   Factura {factura.numero_factura}: SIN NIT")
                continue

            # Buscar en tabla de asignaciones
            try:
                result = db.execute(
                    text(f"SELECT responsable_id FROM {asignacion_table} WHERE nit = :nit AND activo = 1 LIMIT 1"),
                    {"nit": nit}
                ).first()

                if result:
                    responsable_id = result[0]
                    usuario = db.query(Usuario).filter(Usuario.id == responsable_id).first()
                    usuario_name = usuario.usuario if usuario else "DESCONOCIDO"
                    logger.info(f"   Factura {factura.numero_factura} (NIT {nit}): Responsable ID {responsable_id} ({usuario_name})")
                    mapa_nit_responsables[nit] = responsable_id
                else:
                    logger.warning(f"   Factura {factura.numero_factura} (NIT {nit}): SIN RESPONSABLE EN ASIGNACIONES")

            except Exception as e:
                logger.error(f"   Error consultando asignaciones: {e}")

        if len(facturas_auto) > 10:
            logger.info(f"   ... y {len(facturas_auto) - 10} facturas más")

        logger.info(f"\n   Mapa NIT → Responsable: {len(mapa_nit_responsables)} NITs con responsable")

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
