"""
Script para listar facturas que no tienen responsable asignado
y mostrar los NITs que necesitan asignacion
"""
import sys
import os
from pathlib import Path
from collections import Counter

# Agregar el directorio raiz al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.proveedor import Proveedor
from app.models.workflow_aprobacion import AsignacionNitResponsable

def listar_facturas_sin_responsable():
    """Lista facturas sin responsable y los NITs sin asignacion"""
    db: Session = SessionLocal()

    try:
        print("\n" + "="*80)
        print("FACTURAS SIN RESPONSABLE ASIGNADO")
        print("="*80 + "\n")

        # Obtener facturas sin responsable
        facturas_sin_resp = db.query(Factura).filter(
            Factura.responsable_id == None
        ).all()

        print(f"[INFO] Total facturas sin responsable: {len(facturas_sin_resp)}\n")

        # Agrupar por NIT
        nits_sin_asignacion = []

        for factura in facturas_sin_resp:
            if factura.proveedor_id:
                proveedor = db.query(Proveedor).filter(
                    Proveedor.id == factura.proveedor_id
                ).first()

                if proveedor and proveedor.nit:
                    nits_sin_asignacion.append({
                        'nit': proveedor.nit,
                        'razon_social': proveedor.razon_social
                    })

        # Contar NITs unicos
        nit_counter = Counter([item['nit'] for item in nits_sin_asignacion])

        print("NITs SIN ASIGNACION DE RESPONSABLE:")
        print("-" * 80)

        for item in nits_sin_asignacion:
            # Verificar si ya existe asignacion
            asignacion = db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == item['nit'],
                AsignacionNitResponsable.activo == True
            ).first()

            if not asignacion:
                cantidad = nit_counter[item['nit']]
                print(f"\nNIT: {item['nit']}")
                print(f"Razon Social: {item['razon_social']}")
                print(f"Facturas afectadas: {cantidad}")

        print("\n" + "="*80)

    except Exception as e:
        print(f"\n[ERROR] Error: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    listar_facturas_sin_responsable()
