"""
Script para ejecutar el workflow automático con el nuevo sistema de clasificación.
Procesa facturas pendientes y muestra estadísticas comparativas.
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.services.workflow_automatico import WorkflowAutomaticoService
from app.models.factura import Factura
from app.models.workflow_aprobacion import WorkflowAprobacionFactura, EstadoFacturaWorkflow


def main():
    db = SessionLocal()

    try:
        print("=" * 80)
        print("EJECUTANDO WORKFLOW AUTOMATICO CON CLASIFICACION DE PROVEEDORES")
        print("=" * 80)
        print()

        # Estadísticas ANTES
        print("ESTADISTICAS ANTES:")
        total_workflows_antes = db.query(WorkflowAprobacionFactura).count()
        aprobadas_auto_antes = db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.APROBADA_AUTO
        ).count()

        if total_workflows_antes > 0:
            tasa_antes = (aprobadas_auto_antes / total_workflows_antes) * 100
            print(f"  Total workflows existentes: {total_workflows_antes}")
            print(f"  Aprobadas automáticamente: {aprobadas_auto_antes}")
            print(f"  Tasa de auto-aprobación: {tasa_antes:.1f}%")
        else:
            print("  Sin workflows previos")

        print()

        # Obtener facturas pendientes
        facturas_pendientes = db.query(Factura).filter(
            ~Factura.id.in_(db.query(WorkflowAprobacionFactura.factura_id))
        ).all()

        print(f"Facturas pendientes de procesar: {len(facturas_pendientes)}")
        print()

        if not facturas_pendientes:
            print("No hay facturas pendientes. Terminando.")
            return

        # Procesar facturas
        servicio = WorkflowAutomaticoService(db)
        resultados = {
            'total': 0,
            'aprobadas_auto': 0,
            'en_revision': 0,
            'errores': 0,
            'detalles': []
        }

        print("Procesando facturas...")
        print()

        for i, factura in enumerate(facturas_pendientes, 1):
            try:
                resultado = servicio.procesar_factura_nueva(factura.id)
                resultados['total'] += 1

                if resultado.get('exito'):
                    estado = resultado.get('estado')
                    if estado == 'APROBADA_AUTO':
                        resultados['aprobadas_auto'] += 1
                        simbolo = "[AUTO-OK]"
                    else:
                        resultados['en_revision'] += 1
                        simbolo = "[REVISION]"

                    # Obtener info del proveedor
                    nit = resultado.get('nit_proveedor', 'Sin NIT')
                    proveedor = factura.proveedor.razon_social[:40] if factura.proveedor else 'Sin proveedor'
                    monto = float(factura.total_a_pagar) if factura.total_a_pagar else 0

                    print(f"{simbolo} {i}/{len(facturas_pendientes)} - "
                          f"Factura {factura.numero_factura} - {proveedor} - "
                          f"${monto:,.0f}")

                    resultados['detalles'].append({
                        'factura_id': factura.id,
                        'numero': factura.numero_factura,
                        'estado': estado,
                        'nit': nit,
                        'proveedor': proveedor,
                        'monto': monto
                    })
                else:
                    resultados['errores'] += 1
                    print(f"[ERROR] {i}/{len(facturas_pendientes)} - "
                          f"Factura {factura.id}: {resultado.get('error', 'Error desconocido')}")

            except Exception as e:
                resultados['errores'] += 1
                print(f"[ERROR] {i}/{len(facturas_pendientes)} - "
                      f"Factura {factura.id}: {str(e)}")

        print()
        print("=" * 80)
        print("RESUMEN DE PROCESAMIENTO")
        print("=" * 80)
        print(f"Total procesadas:         {resultados['total']}")
        print(f"Aprobadas automáticamente: {resultados['aprobadas_auto']}")
        print(f"Requieren revisión:       {resultados['en_revision']}")
        print(f"Errores:                  {resultados['errores']}")
        print()

        if resultados['total'] > 0:
            tasa_nueva = (resultados['aprobadas_auto'] / resultados['total']) * 100
            print(f"TASA DE AUTO-APROBACION (NUEVAS): {tasa_nueva:.1f}%")

        print()

        # Estadísticas DESPUÉS (globales)
        print("=" * 80)
        print("ESTADISTICAS GLOBALES DESPUES")
        print("=" * 80)
        total_workflows_despues = db.query(WorkflowAprobacionFactura).count()
        aprobadas_auto_despues = db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.estado == EstadoFacturaWorkflow.APROBADA_AUTO
        ).count()

        tasa_despues = (aprobadas_auto_despues / total_workflows_despues) * 100

        print(f"Total workflows:          {total_workflows_despues}")
        print(f"Aprobadas automáticamente: {aprobadas_auto_despues}")
        print(f"Tasa de auto-aprobación:  {tasa_despues:.1f}%")

        if total_workflows_antes > 0:
            diferencia = tasa_despues - tasa_antes
            print(f"Cambio respecto a anterior: {diferencia:+.1f}%")

        print()

        # Desglose por proveedor de las nuevas aprobaciones automáticas
        if resultados['aprobadas_auto'] > 0:
            print("=" * 80)
            print("FACTURAS AUTO-APROBADAS (NUEVAS)")
            print("=" * 80)

            auto_aprobadas = [d for d in resultados['detalles'] if d['estado'] == 'APROBADA_AUTO']
            for detalle in auto_aprobadas:
                print(f"  - {detalle['numero']} | {detalle['proveedor']} | ${detalle['monto']:,.0f}")

        print()
        print("Proceso completado exitosamente")

    except Exception as e:
        print(f"ERROR CRITICO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
