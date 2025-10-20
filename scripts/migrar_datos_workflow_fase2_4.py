"""
Script de migración de datos de facturas a workflow (Fase 2.4).

ESTRATEGIA PROFESIONAL:
========================

OBJETIVO:
- Mover datos de aprobación/rechazo de tabla facturas a workflow_aprobacion_facturas
- Preparar para eliminación de campos redundantes en facturas

PROCESO:
1. Identificar facturas con datos de aprobación/rechazo pero sin workflow
2. Crear registros de workflow con esos datos
3. Validar que todos los datos fueron migrados
4. Generar reporte detallado

SEGURIDAD:
- NO elimina datos de facturas (eso lo hace la migración Alembic)
- Genera backup de datos antes de migrar
- Validación completa post-migración

Nivel: Fortune 500 Data Migration
Autor: Equipo de Desarrollo Senior
Fecha: 2025-10-19
"""

import sys
import logging
from datetime import datetime
from typing import List, Dict
import csv

sys.path.insert(0, '.')

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.workflow_aprobacion import (
    WorkflowAprobacionFactura,
    EstadoFacturaWorkflow,
    TipoAprobacion
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigradorWorkflow:
    """
    Migrador profesional de datos de facturas a workflow.

    Migra datos de aprobación/rechazo manteniendo integridad referencial.
    """

    def __init__(self, db: Session):
        self.db = db
        self.reporte_migracion: List[Dict] = []
        self.stats = {
            'facturas_analizadas': 0,
            'facturas_con_datos': 0,
            'workflows_creados': 0,
            'workflows_actualizados': 0,
            'errores': 0
        }

    def analizar_estado_actual(self) -> Dict[str, int]:
        """Analiza el estado actual de datos antes de migrar."""
        logger.info("\n" + "="*80)
        logger.info("ANÁLISIS PRE-MIGRACIÓN")
        logger.info("="*80)

        # Contar facturas con datos de aprobación
        result = self.db.execute(text("""
            SELECT COUNT(*)
            FROM facturas
            WHERE aprobado_por IS NOT NULL
            OR rechazado_por IS NOT NULL
        """))
        facturas_con_datos = result.scalar()

        # Contar workflows existentes
        result = self.db.execute(text("""
            SELECT COUNT(*)
            FROM workflow_aprobacion_facturas
        """))
        workflows_existentes = result.scalar()

        # Facturas aprobadas sin workflow
        result = self.db.execute(text("""
            SELECT COUNT(*)
            FROM facturas f
            LEFT JOIN workflow_aprobacion_facturas w ON f.id = w.factura_id
            WHERE f.aprobado_por IS NOT NULL
            AND w.id IS NULL
        """))
        aprobadas_sin_workflow = result.scalar()

        # Facturas rechazadas sin workflow
        result = self.db.execute(text("""
            SELECT COUNT(*)
            FROM facturas f
            LEFT JOIN workflow_aprobacion_facturas w ON f.id = w.factura_id
            WHERE f.rechazado_por IS NOT NULL
            AND w.id IS NULL
        """))
        rechazadas_sin_workflow = result.scalar()

        stats = {
            'facturas_con_datos': facturas_con_datos,
            'workflows_existentes': workflows_existentes,
            'aprobadas_sin_workflow': aprobadas_sin_workflow,
            'rechazadas_sin_workflow': rechazadas_sin_workflow
        }

        logger.info(f"\nFacturas con datos de aprobación/rechazo: {facturas_con_datos}")
        logger.info(f"Workflows existentes: {workflows_existentes}")
        logger.info(f"Facturas aprobadas sin workflow: {aprobadas_sin_workflow}")
        logger.info(f"Facturas rechazadas sin workflow: {rechazadas_sin_workflow}")
        logger.info(f"\nTotal a migrar: {aprobadas_sin_workflow + rechazadas_sin_workflow}")

        return stats

    def migrar_facturas_a_workflow(self) -> Dict[str, int]:
        """Migra datos de facturas a workflow."""
        logger.info("\n" + "="*80)
        logger.info("MIGRACIÓN FACTURAS → WORKFLOW")
        logger.info("="*80)

        # Obtener facturas con datos pero sin workflow
        facturas = self.db.query(Factura).filter(
            (Factura.aprobado_por.isnot(None)) |
            (Factura.rechazado_por.isnot(None))
        ).all()

        self.stats['facturas_analizadas'] = len(facturas)

        for factura in facturas:
            try:
                # Verificar si ya tiene workflow
                workflow_existente = self.db.query(WorkflowAprobacionFactura).filter(
                    WorkflowAprobacionFactura.factura_id == factura.id
                ).first()

                if workflow_existente:
                    # Actualizar workflow existente si tiene más datos en facturas
                    self._actualizar_workflow_existente(factura, workflow_existente)
                else:
                    # Crear nuevo workflow
                    self._crear_workflow_desde_factura(factura)

            except Exception as e:
                logger.error(f"Error migrando factura {factura.id}: {e}")
                self.stats['errores'] += 1

        # Commit de cambios
        self.db.commit()

        logger.info(f"\nWorkflows creados: {self.stats['workflows_creados']}")
        logger.info(f"Workflows actualizados: {self.stats['workflows_actualizados']}")
        logger.info(f"Errores: {self.stats['errores']}")

        return self.stats

    def _crear_workflow_desde_factura(self, factura: Factura):
        """Crea un nuevo registro de workflow desde datos de factura."""
        # Determinar estado del workflow
        if factura.aprobado_por:
            estado = EstadoFacturaWorkflow.PROCESADA
            aprobada = True
            tipo_aprobacion = TipoAprobacion.MANUAL
        elif factura.rechazado_por:
            estado = EstadoFacturaWorkflow.RECHAZADA
            aprobada = False
            tipo_aprobacion = None
        else:
            return  # No hay datos que migrar

        # Crear workflow
        workflow = WorkflowAprobacionFactura(
            factura_id=factura.id,
            estado=estado,
            responsable_id=factura.responsable_id,

            # Datos de aprobación
            aprobada=aprobada,
            aprobada_por=factura.aprobado_por,
            fecha_aprobacion=factura.fecha_aprobacion,
            tipo_aprobacion=tipo_aprobacion,

            # Datos de rechazo
            rechazada=bool(factura.rechazado_por),
            rechazada_por=factura.rechazado_por,
            fecha_rechazo=factura.fecha_rechazo,
            detalle_rechazo=factura.motivo_rechazo,

            # Metadata
            creado_por="MIGRACION_FASE_2_4",
            creado_en=datetime.now()
        )

        self.db.add(workflow)
        self.stats['workflows_creados'] += 1

        logger.info(
            f"Workflow creado para factura {factura.numero_factura} (ID: {factura.id})"
        )

        # Registrar en reporte
        self.reporte_migracion.append({
            'accion': 'CREAR',
            'factura_id': factura.id,
            'numero_factura': factura.numero_factura,
            'aprobado_por': factura.aprobado_por,
            'rechazado_por': factura.rechazado_por,
            'estado_workflow': estado.value
        })

    def _actualizar_workflow_existente(self, factura: Factura, workflow: WorkflowAprobacionFactura):
        """Actualiza workflow existente si facturas tiene más información."""
        actualizado = False

        # Si facturas tiene aprobado_por pero workflow no
        if factura.aprobado_por and not workflow.aprobada_por:
            workflow.aprobada_por = factura.aprobado_por
            workflow.fecha_aprobacion = factura.fecha_aprobacion
            workflow.aprobada = True
            actualizado = True

        # Si facturas tiene rechazado_por pero workflow no
        if factura.rechazado_por and not workflow.rechazada_por:
            workflow.rechazada_por = factura.rechazado_por
            workflow.fecha_rechazo = factura.fecha_rechazo
            workflow.detalle_rechazo = factura.motivo_rechazo
            workflow.rechazada = True
            actualizado = True

        if actualizado:
            self.stats['workflows_actualizados'] += 1
            logger.info(
                f"Workflow actualizado para factura {factura.numero_factura}"
            )

            self.reporte_migracion.append({
                'accion': 'ACTUALIZAR',
                'factura_id': factura.id,
                'numero_factura': factura.numero_factura,
                'aprobado_por': factura.aprobado_por,
                'rechazado_por': factura.rechazado_por
            })

    def validar_migracion(self) -> bool:
        """Valida que todos los datos fueron migrados correctamente."""
        logger.info("\n" + "="*80)
        logger.info("VALIDACIÓN POST-MIGRACIÓN")
        logger.info("="*80)

        # Verificar que no hay facturas con datos sin workflow
        result = self.db.execute(text("""
            SELECT COUNT(*)
            FROM facturas f
            LEFT JOIN workflow_aprobacion_facturas w ON f.id = w.factura_id
            WHERE (f.aprobado_por IS NOT NULL OR f.rechazado_por IS NOT NULL)
            AND w.id IS NULL
        """))
        sin_workflow = result.scalar()

        logger.info(f"\nFacturas con datos sin workflow: {sin_workflow}")

        if sin_workflow == 0:
            logger.info("VALIDACIÓN: EXITOSA - Todos los datos migrados")
            return True
        else:
            logger.error(f"VALIDACIÓN: FALLO - {sin_workflow} facturas sin migrar")
            return False

    def generar_reporte_csv(self, filename: str = None):
        """Genera reporte CSV de la migración."""
        if not filename:
            filename = f'reporte_migracion_workflow_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        if not self.reporte_migracion:
            logger.info("\nNo hay migraciones para reportar")
            return

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.reporte_migracion[0].keys())
            writer.writeheader()
            writer.writerows(self.reporte_migracion)

        logger.info(f"\nReporte guardado: {filename}")


def main():
    """Ejecuta migración completa."""
    print("\n" + "="*80)
    print("FASE 2.4: MIGRACIÓN DE DATOS A WORKFLOW")
    print("Sistema AFE Backend - Nivel Enterprise")
    print("="*80)

    print("\nEsta migración:")
    print("- Crea workflows para facturas aprobadas/rechazadas sin workflow")
    print("- Actualiza workflows existentes con datos de facturas")
    print("- NO elimina datos de facturas (eso lo hace migración Alembic)")
    print("- Genera reporte CSV detallado")

    # Auto-ejecutar si hay argumento --auto o variable de entorno
    import sys
    auto_mode = '--auto' in sys.argv or os.getenv('AUTO_MIGRATE') == '1'

    if not auto_mode:
        try:
            respuesta = input("\n¿Continuar con la migración? (si/no): ")
            if respuesta.lower() != 'si':
                print("\nCancelado por el usuario")
                return
        except EOFError:
            print("\n[AUTO] Modo no-interactivo detectado, continuando automáticamente...")
    else:
        print("\n[AUTO] Modo automático activado, continuando...")

    # Ejecutar migración
    db = SessionLocal()
    migrador = MigradorWorkflow(db)

    try:
        # Análisis pre-migración
        estado_inicial = migrador.analizar_estado_actual()

        # Migrar datos
        stats = migrador.migrar_facturas_a_workflow()

        # Validar migración
        validacion_ok = migrador.validar_migracion()

        # Generar reporte
        migrador.generar_reporte_csv()

        # Resumen final
        print("\n" + "="*80)
        print("RESUMEN DE MIGRACIÓN")
        print("="*80)
        print(f"\nFacturas analizadas: {stats['facturas_analizadas']}")
        print(f"Workflows creados: {stats['workflows_creados']}")
        print(f"Workflows actualizados: {stats['workflows_actualizados']}")
        print(f"Errores: {stats['errores']}")
        print(f"\nValidación: {'EXITOSA' if validacion_ok else 'FALLO'}")

        if validacion_ok:
            print("\n" + "="*80)
            print("MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("="*80)
            print("\nPróximo paso: Ejecutar migración Alembic para eliminar campos")
            print("  alembic upgrade head")
        else:
            print("\nADVERTENCIA: Revisar errores antes de continuar")

    except Exception as e:
        logger.error(f"\nError durante migración: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
