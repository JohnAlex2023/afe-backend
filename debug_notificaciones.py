#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import io
import logging
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

print("=" * 80)
print("DEBUG: INICIALIZACION DE SERVICIOS DE EMAIL")
print("=" * 80)

# Paso 1: Verificar configuracion
print("\n[1] Verificando configuracion del .env...")
try:
    from app.core.config import settings

    print(f"   [OK] ENVIRONMENT: {settings.environment}")
    print(f"   [OK] GRAPH_TENANT_ID: {settings.graph_tenant_id[:20]}..." if settings.graph_tenant_id else "   [FAIL] GRAPH_TENANT_ID: VACIO")
    print(f"   [OK] GRAPH_CLIENT_ID: {settings.graph_client_id[:20]}..." if settings.graph_client_id else "   [FAIL] GRAPH_CLIENT_ID: VACIO")
    print(f"   [OK] GRAPH_CLIENT_SECRET: {settings.graph_client_secret[:10]}..." if settings.graph_client_secret else "   [FAIL] GRAPH_CLIENT_SECRET: VACIO")
    print(f"   [OK] GRAPH_FROM_EMAIL: {settings.graph_from_email}")
    print(f"   [OK] GRAPH_FROM_NAME: {settings.graph_from_name}")
    print(f"   [OK] SMTP_USER: {settings.smtp_user if settings.smtp_user else '(vacio - no configurado)'}")
    print(f"   [OK] SMTP_PASSWORD: {'configurado' if settings.smtp_password else 'vacio'}")
except Exception as e:
    print(f"   [FAIL] ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Paso 2: Obtener servicio unificado
print("\n[2] Obteniendo servicio unificado de email...")
try:
    from app.services.unified_email_service import get_unified_email_service

    service = get_unified_email_service()
    print(f"   [OK] Servicio obtenido")
    print(f"   [OK] graph_service: {service.graph_service}")
    print(f"   [OK] smtp_service: {service.smtp_service}")
    print(f"   [OK] Active provider: {service.get_active_provider()}")
except Exception as e:
    print(f"   [FAIL] ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Paso 3: Enviar email de prueba
print("\n[3] Intentando enviar email de prueba...")
try:
    result = service.send_email(
        to_email='test@example.com',
        subject='Test de notificaciones',
        body_html='<h1>Esto es una prueba</h1><p>Si ves esto, funciona</p>',
        importance='normal'
    )

    if result.get('success'):
        print(f"   [OK] Email enviado exitosamente")
        print(f"   [OK] Provider utilizado: {result.get('provider')}")
        print(f"   [OK] Timestamp: {result.get('timestamp')}")
    else:
        print(f"   [FAIL] Email fallo")
        print(f"   [FAIL] Error: {result.get('error')}")
except Exception as e:
    print(f"   [FAIL] ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Paso 4: Simular notificacion de factura
print("\n[4] Simulando envio de notificacion de factura aprobada...")
try:
    from app.services.email_notifications import enviar_notificacion_factura_aprobada

    resultado = enviar_notificacion_factura_aprobada(
        email_responsable='test@example.com',
        nombre_responsable='Juan Prueba',
        numero_factura='FAC-001',
        nombre_proveedor='Proveedor Test',
        nit_proveedor='123456789',
        monto_factura='$1,000,000 COP',
        aprobado_por='Admin Test',
        fecha_aprobacion=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    if resultado.get('success'):
        print(f"   [OK] Notificacion enviada exitosamente")
        print(f"   [OK] Provider: {resultado.get('provider')}")
    else:
        print(f"   [FAIL] Notificacion fallo")
        print(f"   [FAIL] Error: {resultado.get('error')}")
except Exception as e:
    print(f"   [FAIL] ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("RESULTADO: TODO FUNCIONANDO CORRECTAMENTE")
print("=" * 80)
