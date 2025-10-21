# -*- coding: utf-8 -*-
"""
Script para probar las notificaciones programadas manualmente.

Permite ejecutar:
- Resumen semanal
- Alertas urgentes
- Notificación de nueva factura

Sin esperar a los horarios programados.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

def main():
    from app.db.session import SessionLocal
    from app.services.notificaciones_programadas import NotificacionesProgramadasService

    print("\n" + "=" * 80)
    print("TEST - NOTIFICACIONES PROGRAMADAS")
    print("=" * 80)
    print("\nOpciones:")
    print("1. Enviar resumen semanal a todos los responsables")
    print("2. Enviar alertas urgentes (facturas > 10 dias)")
    print("3. Notificar nueva factura (requiere ID)")
    print("0. Salir")
    print("-" * 80)

    opcion = input("\nSelecciona una opcion: ").strip()

    db = SessionLocal()

    try:
        service = NotificacionesProgramadasService(db)

        if opcion == "1":
            print("\nEjecutando resumen semanal...")
            resultado = service.enviar_resumen_semanal()

            print(f"\nRESULTADO:")
            print(f"  Total responsables: {resultado['total_responsables']}")
            print(f"  Emails enviados: {resultado['emails_enviados']}")
            print(f"  Emails fallidos: {resultado['emails_fallidos']}")
            print(f"  Responsables sin facturas: {resultado['responsables_sin_facturas']}")

            if resultado['errores']:
                print(f"\nErrores:")
                for error in resultado['errores']:
                    print(f"  - {error['responsable']}: {error['error']}")

        elif opcion == "2":
            print("\nEjecutando alertas urgentes...")
            resultado = service.enviar_alertas_urgentes()

            print(f"\nRESULTADO:")
            print(f"  Total facturas urgentes: {resultado['total']}")
            print(f"  Facturas notificadas: {resultado['enviados']}")
            print(f"  Fallidos: {resultado['fallidos']}")

        elif opcion == "3":
            factura_id = input("\nIngresa el ID de la factura: ").strip()

            if not factura_id.isdigit():
                print("ERROR: ID debe ser un numero")
                return

            print(f"\nNotificando nueva factura ID {factura_id}...")
            resultado = service.notificar_nueva_factura(int(factura_id))

            if resultado.get('success'):
                print(f"\nEXITO: Notificacion enviada")
                print(f"  Provider: {resultado.get('provider')}")
            else:
                print(f"\nERROR: {resultado.get('error')}")

        elif opcion == "0":
            print("\nSaliendo...")
        else:
            print("\nOpcion invalida")

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
