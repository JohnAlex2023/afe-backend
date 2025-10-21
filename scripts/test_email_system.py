# -*- coding: utf-8 -*-
"""
Script de prueba para el sistema de notificaciones por email.

Este script permite probar el envío de emails usando:
- Microsoft Graph API (principal)
- SMTP (fallback)

Uso:
    python scripts/test_email_system.py

El script te pedirá interactivamente:
1. Email de destino
2. Tipo de prueba a realizar
"""

import sys
import os
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar el directorio raíz al path para importar módulos
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import logging
from datetime import datetime

from app.services.unified_email_service import get_unified_email_service
from app.services.email_notifications import (
    enviar_notificacion_factura_aprobada,
    enviar_notificacion_factura_rechazada,
    enviar_notificacion_factura_pendiente,
    enviar_codigo_2fa,
    enviar_recuperacion_password
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def print_header(text: str):
    """Imprime un encabezado formateado."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_result(resultado: dict):
    """Imprime el resultado del envío de email."""
    if resultado.get('success'):
        print("\n  EMAIL ENVIADO EXITOSAMENTE")
        print(f"   Proveedor: {resultado.get('provider', 'unknown')}")
        print(f"   Timestamp: {resultado.get('timestamp', 'N/A')}")
        if resultado.get('recipients'):
            print(f"   Destinatarios: {', '.join(resultado['recipients'])}")
    else:
        print("\n ERROR AL ENVIAR EMAIL")
        print(f"   Error: {resultado.get('error', 'Unknown error')}")
        print(f"   Proveedor: {resultado.get('provider', 'unknown')}")


def test_provider_status():
    """Verifica el estado de los proveedores de email."""
    print_header("1. Verificar Estado de Proveedores")

    service = get_unified_email_service()
    proveedor = service.get_active_provider()

    print(f" Proveedor activo: {proveedor}")

    if proveedor == "microsoft_graph":
        print("     Microsoft Graph está configurado y activo")
    elif proveedor == "smtp":
        print("     Solo SMTP está disponible (Graph no configurado)")
    else:
        print("    Ningún proveedor de email está configurado")
        print("   Por favor verifica tu archivo .env")
        return False

    return True


def test_simple_email(email_destino: str):
    """Prueba de envío simple."""
    print_header("2. Prueba de Email Simple")

    service = get_unified_email_service()

    resultado = service.send_email(
        to_email=email_destino,
        subject="🧪 Test - Sistema de Notificaciones AFE",
        body_html=f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h1 style="color: #007bff;">  Test Email - Sistema AFE</h1>
            <p>Si estás viendo este email, el sistema de notificaciones está funcionando correctamente.</p>

            <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>Detalles de la Prueba:</h3>
                <ul>
                    <li><strong>Fecha/Hora:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</li>
                    <li><strong>Sistema:</strong> AFE Backend - Notificaciones</li>
                    <li><strong>Tipo:</strong> Email de prueba</li>
                </ul>
            </div>

            <p style="color: #666; font-size: 12px;">
                Este es un correo de prueba generado automáticamente.<br>
                Sistema AFE - Gestión de Facturas Electrónicas
            </p>
        </body>
        </html>
        """,
        importance="normal"
    )

    print_result(resultado)
    return resultado.get('success', False)


def test_factura_aprobada(email_destino: str):
    """Prueba de notificación de factura aprobada."""
    print_header("3. Prueba de Factura Aprobada")

    resultado = enviar_notificacion_factura_aprobada(
        email_responsable=email_destino,
        nombre_responsable="Usuario de Prueba",
        numero_factura="TEST-2025-001",
        nombre_proveedor="Proveedor de Prueba S.A.S",
        nit_proveedor="900.123.456-7",
        monto_factura="$1,500,000 COP",
        aprobado_por="Sistema AFE (Test)",
        fecha_aprobacion=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    print_result(resultado)
    return resultado.get('success', False)


def test_factura_rechazada(email_destino: str):
    """Prueba de notificación de factura rechazada."""
    print_header("4. Prueba de Factura Rechazada")

    resultado = enviar_notificacion_factura_rechazada(
        email_responsable=email_destino,
        nombre_responsable="Usuario de Prueba",
        numero_factura="TEST-2025-002",
        nombre_proveedor="Proveedor de Prueba Ltda",
        nit_proveedor="800.987.654-3",
        monto_factura="$2,000,000 COP",
        rechazado_por="Sistema AFE (Test)",
        motivo_rechazo="Esta es una prueba del sistema de notificaciones. Los valores no coinciden con la orden de compra.",
        fecha_rechazo=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    print_result(resultado)
    return resultado.get('success', False)


def test_factura_pendiente(email_destino: str):
    """Prueba de notificación de factura pendiente."""
    print_header("5. Prueba de Factura Pendiente")

    resultado = enviar_notificacion_factura_pendiente(
        email_responsable=email_destino,
        nombre_responsable="Usuario de Prueba",
        numero_factura="TEST-2025-003",
        nombre_proveedor="Servicios de Prueba S.A.",
        nit_proveedor="900.555.666-8",
        monto_factura="$5,000,000 COP",
        fecha_recepcion=datetime.now().strftime("%Y-%m-%d"),
        centro_costos="IT-INFRAESTRUCTURA",
        dias_pendiente=3,
        link_sistema="https://afe.zentria.com.co/facturas/TEST-2025-003"
    )

    print_result(resultado)
    return resultado.get('success', False)


def test_codigo_2fa(email_destino: str):
    """Prueba de código 2FA."""
    print_header("6. Prueba de Código 2FA")

    resultado = enviar_codigo_2fa(
        email_usuario=email_destino,
        nombre_usuario="Usuario de Prueba",
        codigo_2fa="123456",
        minutos_validez=10
    )

    print_result(resultado)
    return resultado.get('success', False)


def test_recuperacion_password(email_destino: str):
    """Prueba de recuperación de contraseña."""
    print_header("7. Prueba de Recuperación de Contraseña")

    resultado = enviar_recuperacion_password(
        email_usuario=email_destino,
        nombre_usuario="Usuario de Prueba",
        link_recuperacion="https://afe.zentria.com.co/reset-password?token=test-token-12345",
        minutos_validez=30,
        ip_address="127.0.0.1"
    )

    print_result(resultado)
    return resultado.get('success', False)


def menu_principal():
    """Muestra el menú principal y ejecuta las pruebas."""
    print("\n" + "=" * 80)
    print("  🧪 SISTEMA DE PRUEBAS - NOTIFICACIONES POR EMAIL")
    print("  Sistema AFE - Gestión de Facturas Electrónicas")
    print("=" * 80)

    # Verificar estado de proveedores
    if not test_provider_status():
        print("\n  No se puede continuar sin un proveedor de email configurado.")
        print("Por favor configura Microsoft Graph o SMTP en tu archivo .env")
        return

    # Solicitar email de destino
    print("\n📧 Por favor ingresa el email de destino para las pruebas:")
    email_destino = input("   Email: ").strip()

    if not email_destino or '@' not in email_destino:
        print(" Email inválido")
        return

    print(f"\n  Enviando emails de prueba a: {email_destino}")

    # Menú de opciones
    while True:
        print("\n" + "-" * 80)
        print("OPCIONES DE PRUEBA:")
        print("-" * 80)
        print("1. Email simple (prueba básica)")
        print("2. Factura aprobada")
        print("3. Factura rechazada")
        print("4. Factura pendiente")
        print("5. Código 2FA")
        print("6. Recuperación de contraseña")
        print("7. TODAS las pruebas")
        print("0. Salir")
        print("-" * 80)

        opcion = input("\nSelecciona una opción: ").strip()

        if opcion == "0":
            print("\n👋 Saliendo...")
            break
        elif opcion == "1":
            test_simple_email(email_destino)
        elif opcion == "2":
            test_factura_aprobada(email_destino)
        elif opcion == "3":
            test_factura_rechazada(email_destino)
        elif opcion == "4":
            test_factura_pendiente(email_destino)
        elif opcion == "5":
            test_codigo_2fa(email_destino)
        elif opcion == "6":
            test_recuperacion_password(email_destino)
        elif opcion == "7":
            print("\n Ejecutando TODAS las pruebas...")
            resultados = []
            resultados.append(test_simple_email(email_destino))
            resultados.append(test_factura_aprobada(email_destino))
            resultados.append(test_factura_rechazada(email_destino))
            resultados.append(test_factura_pendiente(email_destino))
            resultados.append(test_codigo_2fa(email_destino))
            resultados.append(test_recuperacion_password(email_destino))

            print("\n" + "=" * 80)
            print("  RESUMEN DE PRUEBAS")
            print("=" * 80)
            exitosos = sum(resultados)
            total = len(resultados)
            print(f"\n  Exitosos: {exitosos}/{total}")
            print(f" Fallidos: {total - exitosos}/{total}")

            if exitosos == total:
                print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
            else:
                print("\n  Algunas pruebas fallaron. Revisa los logs arriba.")
        else:
            print(" Opción inválida")

        input("\nPresiona ENTER para continuar...")


if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n👋 Interrumpido por el usuario. Saliendo...")
    except Exception as e:
        logger.error(f"Error en el script de pruebas: {str(e)}", exc_info=True)
        print(f"\n ERROR: {str(e)}")
        sys.exit(1)
