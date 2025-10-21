# -*- coding: utf-8 -*-
"""
Script completo para probar el sistema de notificaciones integrado.
Simula el flujo completo de aprobación/rechazo de facturas.
"""

import sys
import os
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

def main():
    print("\n" + "=" * 80)
    print("PRUEBA COMPLETA - SISTEMA DE NOTIFICACIONES INTEGRADO")
    print("=" * 80 + "\n")

    try:
        from app.services.email_notifications import (
            enviar_notificacion_factura_aprobada,
            enviar_notificacion_factura_rechazada,
            enviar_notificacion_factura_pendiente
        )
        from datetime import datetime

        # Solicitar email de destino
        email = input("Ingresa el email de destino para pruebas: ").strip()

        if not email or '@' not in email:
            print(" Email inválido")
            return False

        print(f"\n  Enviando pruebas a: {email}")
        print("\n" + "-" * 80)

        # PRUEBA 1: Factura Aprobada
        print("\n1️⃣  Enviando notificación de FACTURA APROBADA...")
        resultado1 = enviar_notificacion_factura_aprobada(
            email_responsable=email,
            nombre_responsable="Usuario de Prueba",
            numero_factura="TEST-2025-001",
            nombre_proveedor="Proveedor Ejemplo S.A.S",
            nit_proveedor="900.123.456-7",
            monto_factura="$2,500,000.00 COP",
            aprobado_por="Carlos Administrador",
            fecha_aprobacion=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        if resultado1.get('success'):
            print(f"     Enviado vía {resultado1.get('provider')}")
        else:
            print(f"    Error: {resultado1.get('error')}")

        # PRUEBA 2: Factura Rechazada
        print("\n2️⃣  Enviando notificación de FACTURA RECHAZADA...")
        resultado2 = enviar_notificacion_factura_rechazada(
            email_responsable=email,
            nombre_responsable="Usuario de Prueba",
            numero_factura="TEST-2025-002",
            nombre_proveedor="Servicios Corp Ltda",
            nit_proveedor="800.987.654-3",
            monto_factura="$1,800,000.00 COP",
            rechazado_por="Ana Revisora",
            motivo_rechazo="Los valores de la factura no coinciden con la orden de compra OC-12345. Por favor verificar y reenviar.",
            fecha_rechazo=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        if resultado2.get('success'):
            print(f"     Enviado vía {resultado2.get('provider')}")
        else:
            print(f"    Error: {resultado2.get('error')}")

        # PRUEBA 3: Factura Pendiente
        print("\n3️⃣  Enviando notificación de FACTURA PENDIENTE...")
        resultado3 = enviar_notificacion_factura_pendiente(
            email_responsable=email,
            nombre_responsable="Usuario de Prueba",
            numero_factura="TEST-2025-003",
            nombre_proveedor="Tecnología Avanzada S.A.",
            nit_proveedor="900.555.666-8",
            monto_factura="$3,200,000.00 COP",
            fecha_recepcion=datetime.now().strftime("%Y-%m-%d"),
            centro_costos="IT-INFRAESTRUCTURA",
            dias_pendiente=5,
            link_sistema="https://afe.zentria.com.co/facturas/TEST-2025-003"
        )

        if resultado3.get('success'):
            print(f"     Enviado vía {resultado3.get('provider')}")
        else:
            print(f"    Error: {resultado3.get('error')}")

        # Resumen
        print("\n" + "=" * 80)
        print("RESUMEN DE PRUEBAS")
        print("=" * 80)

        exitosos = sum([
            resultado1.get('success', False),
            resultado2.get('success', False),
            resultado3.get('success', False)
        ])

        print(f"\n  Exitosos: {exitosos}/3")
        print(f" Fallidos: {3 - exitosos}/3")

        if exitosos == 3:
            print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
            print("\nRevisa tu bandeja de entrada:")
            print(f"   📧 {email}")
            print("\nDeberías haber recibido 3 emails:")
            print("   1. Factura TEST-2025-001 - APROBADA")
            print("   2. Factura TEST-2025-002 - RECHAZADA")
            print("   3. Factura TEST-2025-003 - PENDIENTE")
        else:
            print("\n  Algunas pruebas fallaron. Revisa los logs arriba.")

        print("\n" + "=" * 80 + "\n")
        return exitosos == 3

    except Exception as e:
        print(f"\n ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario")
        sys.exit(1)
