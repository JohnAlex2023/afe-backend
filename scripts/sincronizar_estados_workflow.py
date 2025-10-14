#!/usr/bin/env python3
"""
Script para sincronizar estados entre workflow_aprobacion_facturas y facturas.

El workflow es la fuente autoritativa de verdad (Single Source of Truth).
Este script actualiza la tabla facturas para reflejar el estado del workflow.

Uso:
    python scripts/sincronizar_estados_workflow.py
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.factura import Factura, EstadoFactura
from app.models.workflow_aprobacion import WorkflowAprobacionFactura, EstadoFacturaWorkflow


# Mapeo autoritativo: EstadoFacturaWorkflow -> EstadoFactura
MAPEO_ESTADOS = {
    EstadoFacturaWorkflow.RECIBIDA: EstadoFactura.pendiente,
    EstadoFacturaWorkflow.EN_ANALISIS: EstadoFactura.pendiente,
    EstadoFacturaWorkflow.APROBADA_AUTO: EstadoFactura.aprobada_auto,
    EstadoFacturaWorkflow.APROBADA_MANUAL: EstadoFactura.aprobada,
    EstadoFacturaWorkflow.RECHAZADA: EstadoFactura.rechazada,
    EstadoFacturaWorkflow.PENDIENTE_REVISION: EstadoFactura.en_revision,
    EstadoFacturaWorkflow.EN_REVISION: EstadoFactura.en_revision,
    EstadoFacturaWorkflow.OBSERVADA: EstadoFactura.en_revision,
    EstadoFacturaWorkflow.ENVIADA_CONTABILIDAD: EstadoFactura.aprobada,
    EstadoFacturaWorkflow.PROCESADA: EstadoFactura.pagada,
}


def sincronizar_estados():
    """
    Sincroniza todos los estados de facturas según el workflow.
    """
    db: Session = SessionLocal()

    try:
        print("=" * 70)
        print("SINCRONIZACION DE ESTADOS WORKFLOW -> FACTURAS")
        print("=" * 70)
        print()

        # Obtener todos los workflows
        workflows = db.query(WorkflowAprobacionFactura).all()

        if not workflows:
            print("[ERROR] No hay workflows en la base de datos")
            return

        print(f"Total workflows encontrados: {len(workflows)}")
        print()

        stats = {
            "total": 0,
            "actualizados": 0,
            "ya_sincronizados": 0,
            "sin_factura": 0,
            "por_estado": {}
        }

        # Procesar cada workflow
        for workflow in workflows:
            stats["total"] += 1

            if not workflow.factura:
                stats["sin_factura"] += 1
                print(f"[WARN] Workflow {workflow.id} no tiene factura asociada")
                continue

            # Determinar estado correcto
            nuevo_estado = MAPEO_ESTADOS.get(workflow.estado, EstadoFactura.pendiente)
            estado_actual = workflow.factura.estado

            # Contar por estado
            estado_key = workflow.estado.value
            stats["por_estado"][estado_key] = stats["por_estado"].get(estado_key, 0) + 1

            if estado_actual != nuevo_estado:
                # Actualizar estado
                workflow.factura.estado = nuevo_estado

                # Sincronizar campos adicionales
                if workflow.aprobada:
                    workflow.factura.aprobado_por = workflow.aprobada_por
                    workflow.factura.fecha_aprobacion = workflow.fecha_aprobacion

                if workflow.rechazada:
                    workflow.factura.rechazado_por = workflow.rechazada_por
                    workflow.factura.fecha_rechazo = workflow.fecha_rechazo
                    workflow.factura.motivo_rechazo = workflow.detalle_rechazo

                stats["actualizados"] += 1
                print(f"[OK] Factura {workflow.factura.numero_factura}: {estado_actual.value} -> {nuevo_estado.value}")
            else:
                stats["ya_sincronizados"] += 1

        # Commit de todos los cambios
        db.commit()

        print()
        print("=" * 70)
        print("RESUMEN DE SINCRONIZACIÓN")
        print("=" * 70)
        print(f"Total workflows procesados:    {stats['total']}")
        print(f"Estados actualizados:          {stats['actualizados']}")
        print(f"Ya sincronizados:              {stats['ya_sincronizados']}")
        print(f"Sin factura asociada:          {stats['sin_factura']}")
        print()
        print("Distribución por estado workflow:")
        for estado, cantidad in sorted(stats["por_estado"].items()):
            print(f"  {estado:<30} {cantidad:>5}")
        print("=" * 70)

        return stats

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Punto de entrada principal"""
    try:
        stats = sincronizar_estados()

        if stats and stats["actualizados"] > 0:
            print(f"\n[OK] Sincronizacion completada: {stats['actualizados']} facturas actualizadas")
            sys.exit(0)
        elif stats and stats["actualizados"] == 0:
            print("\n[OK] Todas las facturas ya estaban sincronizadas")
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n[ERROR] Sincronizacion interrumpida por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] ERROR CRITICO: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
