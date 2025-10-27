# -*- coding: utf-8 -*-
"""
Script para verificar las credenciales de Microsoft Graph.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verificar_credenciales():
    """Verifica que las credenciales de Microsoft Graph esten configuradas."""
    print("\n" + "=" * 80)
    print("VERIFICACION DE CREDENCIALES MICROSOFT GRAPH")
    print("=" * 80 + "\n")

    try:
        from app.core.config import settings

        print("1. Verificando variables de entorno...")
        print(f"   GRAPH_TENANT_ID: {'OK' if settings.graph_tenant_id else 'FALTA'}")
        print(f"   GRAPH_CLIENT_ID: {'OK' if settings.graph_client_id else 'FALTA'}")
        print(f"   GRAPH_CLIENT_SECRET: {'OK' if settings.graph_client_secret else 'FALTA'}")
        print(f"   GRAPH_FROM_EMAIL: {settings.graph_from_email}")
        print(f"   GRAPH_FROM_NAME: {settings.graph_from_name}")

        if not all([settings.graph_tenant_id, settings.graph_client_id, settings.graph_client_secret]):
            print("\nERROR: Faltan credenciales de Microsoft Graph en el archivo .env")
            return False

        print("\n2. Intentando obtener token de Microsoft Graph...")
        from app.services.microsoft_graph_email_service import get_graph_email_service

        service = get_graph_email_service(
            tenant_id=settings.graph_tenant_id,
            client_id=settings.graph_client_id,
            client_secret=settings.graph_client_secret,
            from_email=settings.graph_from_email,
            from_name=settings.graph_from_name
        )

        # Intentar obtener token
        token = service._get_token()

        if token:
            print("   OK - Token obtenido exitosamente")
            print(f"   Token preview: {token[:20]}...")
            print(f"   Token expira: {service.token_expires}")
            print("\nEXITO: Las credenciales de Microsoft Graph son validas")
            return True
        else:
            print("   ERROR - No se pudo obtener el token")
            return False

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        logger.error("Error verificando credenciales", exc_info=True)
        return False


if __name__ == "__main__":
    success = verificar_credenciales()
    print("\n" + "=" * 80 + "\n")
    sys.exit(0 if success else 1)
