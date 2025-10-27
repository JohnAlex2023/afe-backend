"""
Script para ejecutar el proceso de automatizacion de facturas.

Este script:
1. Asigna responsables a facturas segun configuracion NIT
2. Compara con facturas del mes anterior
3. Aprueba automaticamente si son identicas
4. Crea registros de workflow

Uso:
    python -m scripts.ejecutar_automatizacion
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from datetime import datetime
import requests


def ejecutar_automatizacion_via_api(mes: int = None, anio: int = None):
    """
    Ejecuta la automatizacion via API.
    """
    if mes is None:
        mes = datetime.now().month
    if anio is None:
        anio = datetime.now().year

    print("\n" + "=" * 80)
    print("EJECUCION DE AUTOMATIZACION DE FACTURAS")
    print("=" * 80)
    print(f"\nMes: {mes}/{anio}")

    # Endpoint de automatizacion
    url = "http://localhost:8000/api/v1/automatizacion/procesar"

    print(f"\nEjecutando POST a: {url}")
    print(f"Payload: {{ \"mes\": {mes}, \"anio\": {anio} }}")

    try:
        response = requests.post(
            url,
            json={"mes": mes, "anio": anio},
            timeout=300  # 5 minutos timeout
        )

        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            resultado = response.json()

            print("\n" + "=" * 80)
            print("RESULTADO DE LA AUTOMATIZACION:")
            print("=" * 80)

            # Resumen
            resumen = resultado.get('resumen', {})
            print(f"\nFacturas procesadas: {resumen.get('total_procesadas', 0)}")
            print(f"Aprobadas automaticamente: {resumen.get('aprobadas_auto', 0)}")
            print(f"Pendientes revision: {resumen.get('pendientes_revision', 0)}")
            print(f"Con errores: {resumen.get('errores', 0)}")

            # Detalles
            if 'detalles' in resultado:
                detalles = resultado['detalles']
                print(f"\nTiempo ejecucion: {detalles.get('tiempo_ejecucion', 'N/A')}")
                print(f"Timestamp: {detalles.get('timestamp', 'N/A')}")

            print("\n" + "=" * 80)
            print("[OK] Automatizacion ejecutada exitosamente")
            print("=" * 80)

            return resultado

        else:
            print(f"\n[ERROR] La API respondio con error: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print("\n[ERROR] No se pudo conectar al servidor")
        print("Asegurate de que el backend este corriendo en http://localhost:8000")
        return None
    except requests.exceptions.Timeout:
        print("\n[ERROR] Timeout - El proceso tomo mas de 5 minutos")
        return None
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


def ejecutar_automatizacion_directo(db: Session, mes: int = None, anio: int = None):
    """
    Ejecuta la automatizacion directamente (sin API).
    Alternativa si la API no esta disponible.
    """
    if mes is None:
        mes = datetime.now().month
    if anio is None:
        anio = datetime.now().year

    print("\n" + "=" * 80)
    print("EJECUCION DIRECTA DE AUTOMATIZACION (sin API)")
    print("=" * 80)

    try:
        from app.services.automation.automation_service import AutomationService

        service = AutomationService()

        print(f"\nProcesando facturas pendientes...")

        resultado = service.procesar_facturas_pendientes(db=db, limite_facturas=500)

        print("\n" + "=" * 80)
        print("RESULTADO:")
        print("=" * 80)
        print(f"Procesadas: {resultado.get('facturas_procesadas', 0)}")
        print(f"Aprobadas auto: {resultado.get('aprobadas_automaticamente', 0)}")
        print(f"Pendientes: {resultado.get('enviadas_revision', 0)}")
        print(f"Errores: {resultado.get('errores', 0)}")

        return resultado

    except ImportError as e:
        print(f"\n[ERROR] No se pudo importar el servicio de automatizacion: {e}")
        return None
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Funcion principal."""
    print("\n>> Iniciando script de automatizacion...")

    # Obtener mes y año actual
    mes_actual = datetime.now().month
    anio_actual = datetime.now().year

    print(f"\nMes a procesar: {mes_actual}/{anio_actual}")
    print("\nEstrategia: Intentar via API primero, luego directo si falla")

    # Intento 1: Via API
    print("\n[1] Intentando via API...")
    resultado = ejecutar_automatizacion_via_api(mes=mes_actual, anio=anio_actual)

    if resultado:
        print("\n[OK] Automatizacion completada via API")
        return

    # Intento 2: Directo
    print("\n[2] API no disponible. Intentando ejecucion directa...")
    db = SessionLocal()
    try:
        resultado = ejecutar_automatizacion_directo(db, mes=mes_actual, anio=anio_actual)

        if resultado:
            print("\n[OK] Automatizacion completada directamente")
        else:
            print("\n[ERROR] No se pudo ejecutar la automatizacion")

    finally:
        db.close()


if __name__ == "__main__":
    main()
