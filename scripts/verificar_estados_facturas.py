"""
Script para verificar los estados de las facturas y el workflow de aprobación automática.

Uso:
    python -m scripts.verificar_estados_facturas
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.db.session import SessionLocal
from app.models.factura import Factura, EstadoFactura
from app.models.workflow_aprobacion import WorkflowAprobacionFactura, EstadoFacturaWorkflow
from app.models.proveedor import Proveedor
from app.models.responsable import Responsable


def verificar_estados_facturas(db: Session):
    """Verifica los estados de las facturas en el sistema."""
    print("\n" + "=" * 80)
    print("VERIFICACION DE ESTADOS DE FACTURAS Y WORKFLOW DE APROBACION")
    print("=" * 80)

    # 1. Resumen general de facturas
    print("\n[1] RESUMEN GENERAL DE FACTURAS:")
    print("-" * 80)

    total_facturas = db.query(Factura).count()
    print(f"Total de facturas en el sistema: {total_facturas}")

    if total_facturas == 0:
        print("\n[INFO] No hay facturas en el sistema aun.")
        return

    # Estados de facturas
    print("\nDistribucion por estado:")
    estados = db.query(
        Factura.estado,
        func.count(Factura.id).label('cantidad')
    ).group_by(Factura.estado).all()

    for estado, cantidad in estados:
        porcentaje = (cantidad / total_facturas) * 100
        print(f"  - {estado.value:20s}: {cantidad:5d} ({porcentaje:5.1f}%)")

    # 2. Facturas aprobadas automaticamente
    print("\n[2] FACTURAS APROBADAS AUTOMATICAMENTE:")
    print("-" * 80)

    facturas_auto = db.query(Factura).filter(
        Factura.estado == EstadoFactura.aprobada_auto
    ).count()

    print(f"Total aprobadas automaticamente: {facturas_auto}")

    if facturas_auto > 0:
        print("\nUltimas 10 facturas aprobadas automaticamente:")
        ultimas_auto = db.query(Factura).filter(
            Factura.estado == EstadoFactura.aprobada_auto
        ).order_by(desc(Factura.fecha_procesamiento_auto)).limit(10).all()

        for f in ultimas_auto:
            print(f"\n  Factura #{f.numero_factura}")
            print(f"    ID: {f.id}")
            print(f"    Proveedor: {f.proveedor.razon_social if f.proveedor else 'N/A'}")
            print(f"    Total: ${f.total_a_pagar:,.2f}")
            print(f"    Confianza: {f.confianza_automatica}")
            print(f"    Referencia: Factura #{f.factura_referencia_id if f.factura_referencia_id else 'N/A'}")
            print(f"    Motivo: {f.motivo_decision}")
            print(f"    Fecha procesamiento: {f.fecha_procesamiento_auto}")

    # 3. Workflow de aprobacion
    print("\n[3] WORKFLOW DE APROBACION:")
    print("-" * 80)

    total_workflows = db.query(WorkflowAprobacionFactura).count()
    print(f"Total de registros en workflow: {total_workflows}")

    if total_workflows > 0:
        print("\nDistribucion por estado de workflow:")
        estados_wf = db.query(
            WorkflowAprobacionFactura.estado,
            func.count(WorkflowAprobacionFactura.id).label('cantidad')
        ).group_by(WorkflowAprobacionFactura.estado).all()

        for estado, cantidad in estados_wf:
            porcentaje = (cantidad / total_workflows) * 100
            print(f"  - {estado.value:25s}: {cantidad:5d} ({porcentaje:5.1f}%)")

        # Facturas identicas al mes anterior
        print("\n[INFO] Facturas identicas al mes anterior:")
        identicas = db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.es_identica_mes_anterior == True
        ).count()
        print(f"  Total: {identicas}")

    # 4. Facturas pendientes de revision
    print("\n[4] FACTURAS PENDIENTES DE REVISION:")
    print("-" * 80)

    pendientes = db.query(Factura).filter(
        Factura.estado.in_([EstadoFactura.pendiente, EstadoFactura.en_revision])
    ).count()

    print(f"Total pendientes: {pendientes}")

    if pendientes > 0:
        print("\nUltimas 5 facturas pendientes:")
        ultimas_pend = db.query(Factura).filter(
            Factura.estado.in_([EstadoFactura.pendiente, EstadoFactura.en_revision])
        ).order_by(desc(Factura.creado_en)).limit(5).all()

        for f in ultimas_pend:
            print(f"\n  Factura #{f.numero_factura}")
            print(f"    ID: {f.id}")
            print(f"    Estado: {f.estado.value}")
            print(f"    Proveedor: {f.proveedor.razon_social if f.proveedor else 'N/A'}")
            print(f"    Total: ${f.total_a_pagar:,.2f}")
            print(f"    Responsable: {f.responsable.nombre if f.responsable else 'SIN ASIGNAR'}")

    # 5. Facturas aprobadas manualmente
    print("\n[5] FACTURAS APROBADAS MANUALMENTE:")
    print("-" * 80)

    aprobadas_manual = db.query(Factura).filter(
        Factura.estado == EstadoFactura.aprobada
    ).count()

    print(f"Total aprobadas manualmente: {aprobadas_manual}")

    # 6. Facturas rechazadas
    print("\n[6] FACTURAS RECHAZADAS:")
    print("-" * 80)

    rechazadas = db.query(Factura).filter(
        Factura.estado == EstadoFactura.rechazada
    ).count()

    print(f"Total rechazadas: {rechazadas}")

    if rechazadas > 0:
        print("\nMotivos de rechazo:")
        rechazadas_list = db.query(Factura).filter(
            Factura.estado == EstadoFactura.rechazada
        ).all()

        for f in rechazadas_list[:5]:
            print(f"\n  Factura #{f.numero_factura}")
            print(f"    Rechazada por: {f.rechazado_por}")
            print(f"    Motivo: {f.motivo_rechazo}")
            print(f"    Fecha rechazo: {f.fecha_rechazo}")

    # 7. Estadisticas de proveedores
    print("\n[7] PROVEEDORES CON MAS FACTURAS:")
    print("-" * 80)

    top_proveedores = db.query(
        Proveedor.razon_social,
        Proveedor.nit,
        func.count(Factura.id).label('cantidad')
    ).join(Factura, Factura.proveedor_id == Proveedor.id)\
     .group_by(Proveedor.id)\
     .order_by(desc('cantidad'))\
     .limit(10).all()

    for razon_social, nit, cantidad in top_proveedores:
        print(f"  - {razon_social[:40]:40s} (NIT: {nit}): {cantidad} facturas")

    # 8. Responsables con mas facturas asignadas
    print("\n[8] RESPONSABLES CON MAS FACTURAS ASIGNADAS:")
    print("-" * 80)

    top_responsables = db.query(
        Responsable.nombre,
        Responsable.email,
        func.count(Factura.id).label('cantidad')
    ).join(Factura, Factura.responsable_id == Responsable.id)\
     .group_by(Responsable.id)\
     .order_by(desc('cantidad'))\
     .limit(10).all()

    if top_responsables:
        for nombre, email, cantidad in top_responsables:
            print(f"  - {nombre[:40]:40s} ({email}): {cantidad} facturas")
    else:
        print("  [INFO] No hay responsables asignados aun")

    # 9. Resumen de confianza automatica
    print("\n[9] ANALISIS DE CONFIANZA AUTOMATICA:")
    print("-" * 80)

    facturas_con_confianza = db.query(Factura).filter(
        Factura.confianza_automatica.isnot(None)
    ).all()

    if facturas_con_confianza:
        confianzas = [float(f.confianza_automatica) for f in facturas_con_confianza]
        avg_confianza = sum(confianzas) / len(confianzas)
        max_confianza = max(confianzas)
        min_confianza = min(confianzas)

        print(f"  Total facturas analizadas: {len(facturas_con_confianza)}")
        print(f"  Confianza promedio: {avg_confianza:.2f}")
        print(f"  Confianza maxima: {max_confianza:.2f}")
        print(f"  Confianza minima: {min_confianza:.2f}")

        # Distribucion por rangos
        print("\n  Distribucion por rangos de confianza:")
        rangos = [
            (0.0, 0.3, "Baja (0.0-0.3)"),
            (0.3, 0.6, "Media (0.3-0.6)"),
            (0.6, 0.8, "Alta (0.6-0.8)"),
            (0.8, 1.0, "Muy Alta (0.8-1.0)")
        ]

        for min_r, max_r, label in rangos:
            count = sum(1 for c in confianzas if min_r <= c < max_r or (max_r == 1.0 and c == 1.0))
            print(f"    {label:20s}: {count}")
    else:
        print("  [INFO] No hay facturas con analisis de confianza aun")


def main():
    """Funcion principal."""
    db = SessionLocal()
    try:
        verificar_estados_facturas(db)
        print("\n" + "=" * 80)
        print("[OK] Verificacion completada")
        print("=" * 80 + "\n")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
