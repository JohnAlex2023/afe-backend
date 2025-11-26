#!/usr/bin/env python3
"""
Script para re-enviar notificaciones a las 5 nuevas facturas.
Útil cuando se corrigen bugs en el sistema de notificaciones.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.factura import Factura
from app.services.automation.notification_service import NotificationService

def main():
    """Re-enviar notificaciones."""
    print("=" * 80)
    print("RE-ENVIO DE NOTIFICACIONES - FACTURAS NUEVAS")
    print("=" * 80)

    engine = create_engine(settings.database_url)
    notification_service = NotificationService()

    with Session(engine) as session:
        # Obtener ultimas 5 facturas
        print("\n[1] OBTENIENDO LAS 5 ULTIMAS FACTURAS")
        print("-" * 80)

        facturas = session.query(Factura).order_by(
            Factura.creado_en.desc()
        ).limit(5).all()

        if not facturas:
            print("[ERROR] No se encontraron facturas")
            return False

        print(f"[OK] Se encontraron {len(facturas)} facturas para procesar")

        # Re-enviar notificación a cada factura
        for factura in facturas:
            print(f"\nProcesando: {factura.numero_factura} (ID: {factura.id})")
            print(f"  Estado: {factura.estado_asignacion}")
            print(f"  Responsable: {factura.usuario.nombre if factura.usuario else 'NO ASIGNADO'}")

            if not factura.usuario:
                print(f"  [SKIP] Sin responsable asignado")
                continue

            # Enviar notificación de revisión requerida
            try:
                resultado = notification_service.notificar_revision_requerida(
                    db=session,
                    factura=factura,
                    motivo="Test: Re-enviando notificación después de correcciones",
                    confianza=0.65,
                    patron_detectado="Re-procesamiento",
                    alertas=["Notificación de prueba"],
                    contexto_historico={
                        "items_analizados": 5,
                        "items_ok": 3,
                        "items_con_alertas": 2,
                        "nuevos_items_count": 0
                    }
                )

                if resultado.get('exito'):
                    emails_enviados = resultado.get('notificaciones_enviadas', 0)
                    total = resultado.get('total_responsables', 0)
                    print(f"  [OK] {emails_enviados}/{total} notificaciones enviadas")
                else:
                    error = resultado.get('error', 'Error desconocido')
                    print(f"  [ERROR] {error}")

            except Exception as e:
                print(f"  [EXCEPCION] {str(e)}")
                import traceback
                traceback.print_exc()

    print("\n" + "=" * 80)
    print("FIN DEL RE-ENVIO")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
