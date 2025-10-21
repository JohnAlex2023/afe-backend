# -*- coding: utf-8 -*-
"""
Script rápido de prueba para verificar el sistema de emails.
Prueba directamente el proveedor activo y envía un email de test.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Prueba rápida del sistema de emails."""
    try:
        from app.services.unified_email_service import get_unified_email_service

        print("\n" + "=" * 80)
        print("PRUEBA RAPIDA - SISTEMA DE NOTIFICACIONES")
        print("=" * 80)

        # Obtener servicio
        service = get_unified_email_service()
        proveedor = service.get_active_provider()

        print(f"\nProveedor activo: {proveedor}")

        if proveedor == "microsoft_graph":
            print("OK - Microsoft Graph esta configurado")
        elif proveedor == "smtp":
            print("OK - SMTP esta disponible como fallback")
        else:
            print("ERROR - No hay proveedor de email configurado")
            print("Verifica tu archivo .env")
            return False

        # Solicitar email
        email_destino = input("\nIngresa el email de destino para la prueba: ").strip()

        if not email_destino or '@' not in email_destino:
            print("ERROR - Email invalido")
            return False

        print(f"\nEnviando email de prueba a: {email_destino}")
        print("Espera un momento...")

        # Enviar email de prueba
        from datetime import datetime

        resultado = service.send_email(
            to_email=email_destino,
            subject="TEST - Sistema AFE Notificaciones",
            body_html=f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 style="color: #28a745;">Sistema de Notificaciones AFE</h1>
                <p>Este es un email de prueba del sistema de notificaciones.</p>
                <p><strong>Fecha:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><strong>Proveedor:</strong> {proveedor}</p>
                <hr>
                <p style="color: #666; font-size: 12px;">
                    Sistema AFE - Gestion de Facturas Electronicas
                </p>
            </body>
            </html>
            """,
            importance="normal"
        )

        print("\n" + "=" * 80)
        if resultado.get('success'):
            print("EXITO - Email enviado correctamente")
            print(f"Proveedor usado: {resultado.get('provider', 'unknown')}")
            print(f"Timestamp: {resultado.get('timestamp', 'N/A')}")
        else:
            print("ERROR - No se pudo enviar el email")
            print(f"Error: {resultado.get('error', 'Unknown error')}")
            print(f"Proveedor: {resultado.get('provider', 'unknown')}")
        print("=" * 80 + "\n")

        return resultado.get('success', False)

    except Exception as e:
        logger.error(f"Error en la prueba: {str(e)}", exc_info=True)
        print(f"\nERROR: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario")
        sys.exit(1)
