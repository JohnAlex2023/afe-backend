#!/usr/bin/env python3
"""
Script para sincronizar workflows con los responsables REALES que aprobaron cada factura.

En lugar de distribuir aleatoriamente, busca en el campo 'accion_por' de cada factura
para identificar quién la aprobó realmente, luego lo mapea al usuario correcto del sistema.
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
    """Sincroniza workflows con responsables reales."""
    logger.info("="*100)
    logger.info("SINCRONIZACIÓN DE WORKFLOWS CON RESPONSABLES REALES")
    logger.info("="*100)

    db = SessionLocal()

    try:
        # 1. Obtener todas las facturas aprobadas
        logger.info("\n1. ANALIZANDO QUIÉN APROBÓ CADA FACTURA:")

        facturas = db.query(Factura).filter(
            Factura.estado.in_([
                EstadoFactura.aprobada.value,
                EstadoFactura.aprobada_auto.value,
                EstadoFactura.validada_contabilidad.value,
                EstadoFactura.devuelta_contabilidad.value
            ])
        ).all()

        logger.info(f"   Total de facturas aprobadas: {len(facturas)}")

        # 2. Mapear accion_por → usuario_id
        logger.info("\n2. MAPEANDO APROBADORES A USUARIOS DEL SISTEMA:")

        usuarios_sistema = db.query(Usuario).filter(Usuario.activo == True).all()
        logger.info(f"   Usuarios activos en el sistema: {len(usuarios_sistema)}")

        for u in usuarios_sistema:
            logger.info(f"     - {u.usuario}: {u.nombre}")

        # Crear mapeo: accion_por → usuario_id
        mapeo_usuarios = {}
        for usuario in usuarios_sistema:
            # Intentar coincidencias por usuario/nombre
            mapeo_usuarios[usuario.usuario.lower()] = usuario.id
            if usuario.nombre:
                mapeo_usuarios[usuario.nombre.lower()] = usuario.id

        logger.info(f"\n   Mapeo disponible: {len(mapeo_usuarios)} entradas")

        # 3. Analizar accion_por en facturas
        logger.info("\n3. ANALIZANDO CAMPO 'accion_por' EN FACTURAS:")

        accion_por_unique = db.query(
            Factura.accion_por,
            func.count(Factura.id).label('count')
        ).filter(
            Factura.estado.in_([
                EstadoFactura.aprobada.value,
                EstadoFactura.aprobada_auto.value,
                EstadoFactura.validada_contabilidad.value,
                EstadoFactura.devuelta_contabilidad.value
            ])
        ).group_by(Factura.accion_por).all()

        for accion_por, count in accion_por_unique:
            usuario_id = mapeo_usuarios.get(str(accion_por).lower())
            usuario_info = f"→ Usuario ID: {usuario_id}"
            if usuario_id:
                usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
                if usuario:
                    usuario_info = f"→ Usuario ID {usuario_id}: {usuario.usuario}"
            else:
                usuario_info = f"→ NO ENCONTRADO EN EL SISTEMA"

            logger.info(f"   accion_por='{accion_por}': {count:4d} facturas {usuario_info}")

        # 4. Sincronizar workflows
        logger.info("\n4. SINCRONIZANDO WORKFLOWS CON RESPONSABLES REALES:")

        facturas_con_workflow = 0
        facturas_sin_mapeo = 0
        cambios_realizados = 0

        for factura in facturas:
            workflow = db.query(WorkflowAprobacionFactura).filter(
                WorkflowAprobacionFactura.factura_id == factura.id
            ).first()

            if not workflow:
                continue

            facturas_con_workflow += 1

            # Obtener el usuario ID basado en accion_por
            usuario_id_real = mapeo_usuarios.get(str(factura.accion_por).lower() if factura.accion_por else '')

            if usuario_id_real:
                if workflow.responsable_id != usuario_id_real:
                    usuario_anterior = workflow.responsable_id
                    workflow.responsable_id = usuario_id_real
                    cambios_realizados += 1
                    if cambios_realizados <= 5:  # Mostrar primeros 5
                        logger.info(
                            f"   Factura {factura.numero_factura}: "
                            f"{usuario_anterior} → {usuario_id_real} (accion_por: {factura.accion_por})"
                        )
            else:
                facturas_sin_mapeo += 1

        if cambios_realizados > 5:
            logger.info(f"   ... y {cambios_realizados - 5} cambios más")

        logger.info(f"\n   Facturas con workflow: {facturas_con_workflow}")
        logger.info(f"   Cambios a realizar: {cambios_realizados}")
        logger.info(f"   Sin mapeo disponible: {facturas_sin_mapeo}")

        if cambios_realizados == 0:
            logger.info("\n   ✅ Los workflows ya tienen los responsables correctos.")
            return

        # Confirmar
        logger.info("\n" + "="*100)
        respuesta = input("¿Deseas continuar con la sincronización? (s/n): ").strip().lower()

        if respuesta != 's':
            logger.warning("Operación cancelada.")
            return

        # Ejecutar cambios
        logger.info("\n5. REALIZANDO SINCRONIZACIÓN:")

        cambios_realizados = 0
        for factura in facturas:
            workflow = db.query(WorkflowAprobacionFactura).filter(
                WorkflowAprobacionFactura.factura_id == factura.id
            ).first()

            if not workflow:
                continue

            usuario_id_real = mapeo_usuarios.get(str(factura.accion_por).lower() if factura.accion_por else '')

            if usuario_id_real and workflow.responsable_id != usuario_id_real:
                workflow.responsable_id = usuario_id_real
                cambios_realizados += 1

        db.commit()
        logger.info(f"   ✅ {cambios_realizados} workflows sincronizados exitosamente")

        # 6. Verificar resultado
        logger.info("\n6. VERIFICACIÓN POST-SINCRONIZACIÓN:")

        result = db.query(
            WorkflowAprobacionFactura.responsable_id,
            func.count(WorkflowAprobacionFactura.id).label('count')
        ).group_by(WorkflowAprobacionFactura.responsable_id).order_by(
            WorkflowAprobacionFactura.responsable_id
        ).all()

        for responsable_id, count in result:
            usuario = db.query(Usuario).filter(Usuario.id == responsable_id).first()
            usuario_name = usuario.usuario if usuario else "DESCONOCIDO"
            logger.info(f"   responsable_id={responsable_id} ({usuario_name:20s}): {count:4d} workflows")

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
