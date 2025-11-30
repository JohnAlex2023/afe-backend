#!/usr/bin/env python3
"""
Script para sincronizar workflows con los responsables correctos usando NIT.

El sistema ya tiene implementado AsignacionNitResponsable que mapea:
  NIT del proveedor → responsable_id

Este script:
1. Para cada factura aprobada/automatizada
2. Obtiene el NIT del proveedor
3. Busca en asignacion_nit_responsable el responsable correcto
4. Actualiza el workflow_aprobacion_factura.responsable_id
5. Sincroniza la relación factura.responsable_id si es necesario
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
from sqlalchemy.orm import joinedload
from app.db.session import SessionLocal
from app.models.factura import Factura, EstadoFactura
from app.models.workflow_aprobacion import WorkflowAprobacionFactura, AsignacionNitResponsable
from app.models.usuario import Usuario
from app.models.proveedor import Proveedor
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Sincroniza workflows usando el mapeo NIT → Responsable."""
    logger.info("="*100)
    logger.info("SINCRONIZACIÓN DE WORKFLOWS POR NIT (Usando AsignacionNitResponsable)")
    logger.info("="*100)

    db = SessionLocal()

    try:
        # 1. Verificar que la tabla AsignacionNitResponsable tiene datos
        logger.info("\n1. VERIFICANDO ASIGNACIONES DE NIT:")
        asignaciones_count = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == True
        ).count()
        logger.info(f"   Total de asignaciones activas: {asignaciones_count}")

        if asignaciones_count == 0:
            logger.warning("   ⚠️  No hay asignaciones NIT → Responsable configuradas")
            logger.warning("   Por favor, configura las asignaciones en /asignacion-nit primero")
            return

        # Mostrar ejemplos
        logger.info("\n   Ejemplos de asignaciones:")
        asignaciones_ejemplo = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == True
        ).limit(5).all()

        for asign in asignaciones_ejemplo:
            usuario = asign.usuario
            logger.info(f"     - NIT {asign.nit}: {usuario.usuario} (ID {usuario.id})")

        # 2. Obtener todas las facturas aprobadas
        logger.info("\n2. ANALIZANDO FACTURAS APROBADAS:")
        facturas = db.query(Factura).options(
            joinedload(Factura.proveedor),
            joinedload(Factura.usuario)
        ).filter(
            Factura.estado.in_([
                EstadoFactura.aprobada.value,
                EstadoFactura.aprobada_auto.value,
                EstadoFactura.validada_contabilidad.value,
                EstadoFactura.devuelta_contabilidad.value
            ])
        ).all()

        logger.info(f"   Total de facturas aprobadas: {len(facturas)}")

        # 3. Analizar y sincronizar
        logger.info("\n3. SINCRONIZANDO WORKFLOWS POR NIT:")

        cambios_pendientes = 0
        facturas_sin_proveedor = 0
        facturas_sin_nit = 0
        facturas_sin_asignacion = 0
        cambios_realizados = []

        for factura in facturas:
            # Validar que factura tiene proveedor
            if not factura.proveedor:
                facturas_sin_proveedor += 1
                logger.warning(f"   ⚠️  Factura {factura.numero_factura} (ID {factura.id}) - SIN PROVEEDOR")
                continue

            # Validar que proveedor tiene NIT
            if not factura.proveedor.nit:
                facturas_sin_nit += 1
                logger.warning(f"   ⚠️  Factura {factura.numero_factura} - Proveedor sin NIT")
                continue

            nit = factura.proveedor.nit

            # Obtener workflow de la factura
            workflow = db.query(WorkflowAprobacionFactura).filter(
                WorkflowAprobacionFactura.factura_id == factura.id
            ).first()

            if not workflow:
                logger.warning(f"   ⚠️  Factura {factura.numero_factura} (ID {factura.id}) - SIN WORKFLOW")
                continue

            # Buscar asignación en la tabla
            asignacion = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == nit,
                AsignacionNitResponsable.activo == True
            ).first()

            if not asignacion:
                facturas_sin_asignacion += 1
                logger.warning(
                    f"   ⚠️  Factura {factura.numero_factura} (NIT {nit}) - "
                    f"SIN ASIGNACIÓN en tabla asignacion_nit_responsable"
                )
                continue

            # Verificar si necesita sincronización
            responsable_id_correcto = asignacion.responsable_id

            if workflow.responsable_id != responsable_id_correcto:
                responsable_anterior = workflow.responsable_id
                usuario_anterior = None
                if responsable_anterior:
                    u_ant = db.query(Usuario).filter(Usuario.id == responsable_anterior).first()
                    usuario_anterior = u_ant.usuario if u_ant else f"ID {responsable_anterior}"

                usuario_nuevo = asignacion.usuario.usuario if asignacion.usuario else f"ID {responsable_id_correcto}"

                cambios_pendientes += 1
                cambios_realizados.append({
                    'factura_id': factura.id,
                    'numero_factura': factura.numero_factura,
                    'nit': nit,
                    'responsable_anterior': responsable_anterior,
                    'usuario_anterior': usuario_anterior,
                    'responsable_nuevo': responsable_id_correcto,
                    'usuario_nuevo': usuario_nuevo
                })

                if len(cambios_realizados) <= 10:
                    logger.info(
                        f"   ✓ Factura {factura.numero_factura} (NIT {nit}): "
                        f"{usuario_anterior} → {usuario_nuevo}"
                    )

        if len(cambios_realizados) > 10:
            logger.info(f"   ... y {len(cambios_realizados) - 10} cambios más")

        # Resumen
        logger.info("\n" + "="*100)
        logger.info("RESUMEN PRE-SINCRONIZACIÓN:")
        logger.info(f"  Total de facturas aprobadas: {len(facturas)}")
        logger.info(f"  Facturas sin proveedor: {facturas_sin_proveedor}")
        logger.info(f"  Facturas sin NIT: {facturas_sin_nit}")
        logger.info(f"  Facturas sin asignación NIT configurada: {facturas_sin_asignacion}")
        logger.info(f"  Cambios pendientes: {cambios_pendientes}")
        logger.info("="*100)

        if cambios_pendientes == 0:
            logger.info("\n✅ Los workflows ya tienen los responsables correctos según NIT.")
            return

        # Ejecutar automáticamente sin confirmación
        logger.info("\n" + "="*100)
        logger.info("Ejecutando sincronización automáticamente...")

        # Ejecutar cambios
        logger.info("\n4. REALIZANDO SINCRONIZACIÓN:")

        for cambio in cambios_realizados:
            workflow = db.query(WorkflowAprobacionFactura).filter(
                WorkflowAprobacionFactura.factura_id == cambio['factura_id']
            ).first()

            if workflow:
                workflow.responsable_id = cambio['responsable_nuevo']

        db.commit()
        logger.info(f"\n✅ {len(cambios_realizados)} workflows sincronizados exitosamente")

        # Verificación post-sincronización
        logger.info("\n5. VERIFICACIÓN POST-SINCRONIZACIÓN:")

        result = db.query(
            WorkflowAprobacionFactura.responsable_id,
            func.count(WorkflowAprobacionFactura.id).label('count')
        ).group_by(WorkflowAprobacionFactura.responsable_id).order_by(
            WorkflowAprobacionFactura.responsable_id
        ).all()

        for responsable_id, count in result:
            usuario = db.query(Usuario).filter(Usuario.id == responsable_id).first()
            usuario_name = usuario.usuario if usuario else "DESCONOCIDO"
            logger.info(f"   responsable_id={responsable_id} ({usuario_name:25s}): {count:4d} workflows")

        logger.info("\n" + "="*100)
        logger.info("✅ SINCRONIZACIÓN COMPLETADA")
        logger.info("="*100)

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
