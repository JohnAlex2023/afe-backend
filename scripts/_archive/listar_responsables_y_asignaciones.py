"""
Script para listar todos los responsables y sus asignaciones NIT
"""
import sys
import os
from pathlib import Path

# Agregar el directorio raiz al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.responsable import Responsable
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.proveedor import Proveedor
from sqlalchemy import func

def listar_responsables_y_asignaciones():
    """Lista todos los responsables y sus asignaciones"""
    db: Session = SessionLocal()

    try:
        print("\n" + "="*80)
        print("LISTADO DE RESPONSABLES Y SUS ASIGNACIONES")
        print("="*80 + "\n")

        # Obtener todos los responsables
        responsables = db.query(Responsable).filter(Responsable.activo == True).all()

        print(f"[INFO] Total responsables activos: {len(responsables)}\n")

        for resp in responsables:
            print("-" * 80)
            print(f"RESPONSABLE: {resp.nombre}")
            print(f"  ID: {resp.id}")
            print(f"  Usuario: {resp.usuario}")
            print(f"  Email: {resp.email}")
            print(f"  Activo: {resp.activo}")

            # Buscar asignaciones en AsignacionNitResponsable
            asignaciones_nit = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.responsable_id == resp.id,
                AsignacionNitResponsable.activo == True
            ).all()

            print(f"\n  ASIGNACIONES NIT: {len(asignaciones_nit)}")
            for asig in asignaciones_nit:
                # Buscar proveedor con ese NIT
                proveedor = db.query(Proveedor).filter(Proveedor.nit == asig.nit).first()
                razon_social = proveedor.razon_social if proveedor else "PROVEEDOR NO ENCONTRADO"

                # Contar facturas con ese NIT
                from app.models.factura import Factura
                facturas_count = db.query(func.count(Factura.id)).join(
                    Proveedor, Factura.proveedor_id == Proveedor.id
                ).filter(Proveedor.nit == asig.nit).scalar()

                print(f"    - NIT: {asig.nit:20} | {razon_social:50} | {facturas_count} facturas")

            # Contar facturas asignadas a este responsable
            from app.models.factura import Factura
            facturas_asignadas = db.query(func.count(Factura.id)).filter(
                Factura.responsable_id == resp.id
            ).scalar()

            print(f"\n  FACTURAS ASIGNADAS ACTUALMENTE: {facturas_asignadas}")
            print()

        print("="*80)

    except Exception as e:
        print(f"\n[ERROR] Error: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    listar_responsables_y_asignaciones()
