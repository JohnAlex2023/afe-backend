#!/usr/bin/env python
"""
Script: Asigna facturas huérfanas a usuarios válidos
Resuelve los últimos 10 casos de facturas sin responsable válido
"""

import sys
from pathlib import Path

backend_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, backend_dir)

import os
os.chdir(backend_dir)

from app.db.session import SessionLocal
from app.models.factura import Factura, EstadoAsignacion
from app.models.usuario import Usuario
from app.models.workflow_aprobacion import WorkflowAprobacionFactura, AsignacionNitResponsable
from datetime import datetime

def asignar_facturas_huerfanas():
    """Asigna las últimas facturas huérfanas a usuarios válidos"""
    db = SessionLocal()

    print("\n" + "="*80)
    print("ASIGNACION: Facturas huerfanas a usuarios validos")
    print("="*80)
    print(f"Fecha/Hora: {datetime.now().isoformat()}\n")

    try:
        # Obtener facturas sin responsable
        facturas_sin = db.query(Factura).filter(Factura.responsable_id == None).all()
        print(f"Facturas sin responsable encontradas: {len(facturas_sin)}")

        if not facturas_sin:
            print("[OK] No hay facturas sin responsable. Sistema sincronizado!")
            return True

        # Obtener usuario por defecto (el más disponible: John)
        usuario_default = db.query(Usuario).filter(
            Usuario.usuario == "john.taimalp"
        ).first()

        if not usuario_default:
            # Si no está John, usar el primer usuario activo
            usuario_default = db.query(Usuario).filter(
                Usuario.activo == True
            ).first()

        if not usuario_default:
            print("ERROR: No hay usuarios disponibles en el sistema")
            return False

        print(f"Usuario por defecto para asignacion: {usuario_default.nombre} (ID={usuario_default.id})\n")

        # Agrupar facturas por NIT
        nits_procesados = {}

        for factura in facturas_sin:
            workflow = db.query(WorkflowAprobacionFactura).filter(
                WorkflowAprobacionFactura.factura_id == factura.id
            ).first()

            nit = workflow.nit_proveedor if workflow else "SIN_NIT"

            if nit not in nits_procesados:
                nits_procesados[nit] = []
            nits_procesados[nit].append(factura)

        print("Facturas agrupadas por NIT:")
        for nit, facturas in nits_procesados.items():
            print(f"  {nit}: {len(facturas)} facturas")

            # Intentar encontrar asignacion
            asignacion = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == nit
            ).first() if nit != "SIN_NIT" else None

            responsable_id = asignacion.responsable_id if asignacion else usuario_default.id

            # Verificar que el usuario existe
            usuario_responsable = db.query(Usuario).filter(
                Usuario.id == responsable_id
            ).first()

            if not usuario_responsable:
                print(f"    WARN: Usuario {responsable_id} no existe, usando {usuario_default.nombre}")
                responsable_id = usuario_default.id

            # Asignar todas las facturas de este NIT
            for factura in facturas:
                factura.responsable_id = responsable_id
                factura.estado_asignacion = EstadoAsignacion.asignado
                factura.actualizado_en = datetime.now()

            usuario_asignado = db.query(Usuario).filter(Usuario.id == responsable_id).first()
            print(f"    -> Asignadas a: {usuario_asignado.nombre}")

        db.commit()
        print(f"\n[OK] Todas las facturas huerfanas han sido asignadas")

        # Verificación final
        sin_responsable = db.query(Factura).filter(Factura.responsable_id == None).count()
        con_responsable = db.query(Factura).filter(Factura.responsable_id != None).count()
        total = db.query(Factura).count()

        print(f"\nVerificacion final:")
        print(f"  Total facturas: {total}")
        print(f"  Con responsable: {con_responsable} ({con_responsable/total*100:.1f}%)")
        print(f"  Sin responsable: {sin_responsable} ({sin_responsable/total*100:.1f}%)")

        if sin_responsable == 0:
            print("\n[OK] TODAS las facturas tienen responsable asignado")
            print("="*80)
            print("SINCRONIZACION COMPLETADA EXITOSAMENTE")
            print("="*80)
            return True
        else:
            print(f"\n[WARN] Aun hay {sin_responsable} facturas sin responsable")
            return False

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = asignar_facturas_huerfanas()
    sys.exit(0 if success else 1)
