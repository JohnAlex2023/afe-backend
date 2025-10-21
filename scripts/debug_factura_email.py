# -*- coding: utf-8 -*-
"""
Script para debuggear por qué no se envían emails al aprobar/rechazar facturas.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

def main():
    from app.db.session import SessionLocal
    from app.models.factura import Factura

    db = SessionLocal()

    try:
        # Solicitar ID de factura
        factura_id = input("Ingresa el ID de una factura para debuggear: ").strip()

        if not factura_id.isdigit():
            print("ERROR: ID debe ser un número")
            return

        factura_id = int(factura_id)

        # Buscar factura
        factura = db.query(Factura).filter(Factura.id == factura_id).first()

        if not factura:
            print(f"ERROR: No se encontró factura con ID {factura_id}")
            return

        print("\n" + "=" * 80)
        print(f"DEBUG - FACTURA ID: {factura.id}")
        print("=" * 80)

        print(f"\nNumero: {factura.numero_factura}")
        print(f"Estado: {factura.estado.value if factura.estado else 'N/A'}")
        print(f"Total: ${factura.total_calculado:,.2f}" if factura.total_calculado else "Total: N/A")

        # 1. Responsable directo
        print("\n" + "-" * 80)
        print("1. RESPONSABLE DIRECTO DE LA FACTURA:")
        print("-" * 80)
        if factura.responsable:
            print(f"   ID: {factura.responsable.id}")
            print(f"   Usuario: {factura.responsable.usuario}")
            print(f"   Nombre: {factura.responsable.nombre or 'Sin nombre'}")
            print(f"   Email: {factura.responsable.email or 'SIN EMAIL '}")
        else:
            print("   NO TIENE RESPONSABLE DIRECTO ")

        # 2. Proveedor
        print("\n" + "-" * 80)
        print("2. PROVEEDOR:")
        print("-" * 80)
        if factura.proveedor:
            print(f"   ID: {factura.proveedor.id}")
            print(f"   NIT: {factura.proveedor.nit}")
            print(f"   Razón Social: {factura.proveedor.razon_social}")

            # 3. Asignaciones NIT
            print("\n" + "-" * 80)
            print("3. ASIGNACIONES NIT -> RESPONSABLE:")
            print("-" * 80)

            if hasattr(factura.proveedor, 'asignaciones_nit'):
                asignaciones = factura.proveedor.asignaciones_nit

                if asignaciones:
                    for asig in asignaciones:
                        if asig.responsable:
                            email_status = f"  {asig.responsable.email}" if asig.responsable.email else " SIN EMAIL"
                            print(f"   NIT: {asig.nit}")
                            print(f"   Responsable: {asig.responsable.usuario}")
                            print(f"   Nombre: {asig.responsable.nombre or 'Sin nombre'}")
                            print(f"   Email: {email_status}")
                            print()
                        else:
                            print(f"   NIT: {asig.nit} -> SIN RESPONSABLE ASIGNADO ")
                else:
                    print("   Este proveedor NO TIENE asignaciones NIT ")
            else:
                print("   El modelo Proveedor NO tiene la relación 'asignaciones_nit' ")
        else:
            print("   FACTURA SIN PROVEEDOR ")

        # 4. Diagnóstico final
        print("\n" + "=" * 80)
        print("DIAGNOSTICO:")
        print("=" * 80)

        email_encontrado = None
        fuente = None

        # Buscar email
        if factura.responsable and factura.responsable.email:
            email_encontrado = factura.responsable.email
            fuente = "Responsable directo de la factura"

        elif factura.proveedor and hasattr(factura.proveedor, 'asignaciones_nit'):
            for asig in factura.proveedor.asignaciones_nit:
                if asig.responsable and asig.responsable.email:
                    email_encontrado = asig.responsable.email
                    fuente = f"Asignación NIT {asig.nit}"
                    break

        if email_encontrado:
            print(f"  EMAIL ENCONTRADO: {email_encontrado}")
            print(f"   Fuente: {fuente}")
            print(f"\n  Esta factura DEBERIA enviar emails al aprobar/rechazar")
        else:
            print(" NO SE ENCONTRÓ EMAIL")
            print("\nPOSIBLES CAUSAS:")
            print("1. La factura no tiene responsable directo")
            print("2. El responsable directo no tiene email")
            print("3. El proveedor no tiene asignaciones NIT")
            print("4. Las asignaciones NIT no tienen responsable con email")
            print("\nSOLUCION:")
            print("- Asignar un responsable con email a la factura, O")
            print("- Asignar un responsable con email al NIT del proveedor")

        print("\n" + "=" * 80 + "\n")

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
