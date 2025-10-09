#!/usr/bin/env python
"""
Script de prueba para el sistema de automatización basado en comparación mes anterior.

Este script prueba la nueva funcionalidad que compara facturas del mes actual
con las del mes anterior para aprobación automática.
"""

import sys
from datetime import datetime, date
from decimal import Decimal

# Agregar el directorio raíz al path
sys.path.insert(0, 'C:\\Users\\jhont\\PRIVADO_ODO\\afe-backend')

from app.db.session import SessionLocal
from app.crud import factura as crud_factura
from app.services.automation.automation_service import AutomationService
from app.services.automation.pattern_detector import PatternDetector


def test_comparacion_mes_anterior():
    """
    Prueba la lógica de comparación con el mes anterior.
    """
    print("=" * 80)
    print("TEST: Sistema de Automatización - Comparación Mes Anterior")
    print("=" * 80)
    print()

    db = SessionLocal()

    try:
        # 1. Buscar facturas de septiembre 2025 (mes pasado)
        print("[*] Buscando facturas de Septiembre 2025...")
        facturas_septiembre = db.query(crud_factura.Factura).filter(
            crud_factura.Factura.año_factura == 2025,
            crud_factura.Factura.mes_factura == 9
        ).all()

        print(f"   [OK] Encontradas {len(facturas_septiembre)} facturas en Septiembre 2025")
        print()

        # 2. Buscar facturas de octubre 2025 (mes actual)
        print("[*] Buscando facturas de Octubre 2025...")
        facturas_octubre = db.query(crud_factura.Factura).filter(
            crud_factura.Factura.año_factura == 2025,
            crud_factura.Factura.mes_factura == 10
        ).all()

        print(f"   [OK] Encontradas {len(facturas_octubre)} facturas en Octubre 2025")
        print()

        if not facturas_octubre:
            print("[!] No hay facturas de octubre para probar")
            return

        # 3. Probar la búsqueda de mes anterior para cada factura de octubre
        print("[*] Probando busqueda de mes anterior...")
        print()

        pattern_detector = PatternDetector()

        for i, factura_oct in enumerate(facturas_octubre[:5], 1):  # Solo primeras 5 para el test
            print(f"--- Factura {i} ---")
            print(f"   Numero: {factura_oct.numero_factura}")
            print(f"   Proveedor ID: {factura_oct.proveedor_id}")
            print(f"   Fecha: {factura_oct.fecha_emision}")
            print(f"   Total: ${factura_oct.total_a_pagar:,.2f}")
            print(f"   Estado actual: {factura_oct.estado}")

            # Buscar factura del mes anterior
            factura_anterior = crud_factura.find_factura_mes_anterior(
                db=db,
                proveedor_id=factura_oct.proveedor_id,
                fecha_actual=factura_oct.fecha_emision,
                concepto_hash=factura_oct.concepto_hash,
                concepto_normalizado=factura_oct.concepto_normalizado
            )

            if factura_anterior:
                print(f"   [OK] Factura del mes anterior encontrada:")
                print(f"      - Numero: {factura_anterior.numero_factura}")
                print(f"      - Fecha: {factura_anterior.fecha_emision}")
                print(f"      - Total: ${factura_anterior.total_a_pagar:,.2f}")

                # Comparar montos
                comparacion = pattern_detector.comparar_con_mes_anterior(
                    factura_nueva=factura_oct,
                    factura_mes_anterior=factura_anterior,
                    tolerancia_porcentaje=5.0
                )

                print(f"   [ANALISIS] Resultado de comparacion:")
                print(f"      - Diferencia: {comparacion['diferencia_porcentaje']:.2f}%")
                print(f"      - Montos coinciden: {'SI' if comparacion['montos_coinciden'] else 'NO'}")
                print(f"      - Decision: {comparacion['decision_sugerida']}")
                print(f"      - Confianza: {comparacion['confianza']:.2%}")
                print(f"      - Razon: {comparacion['razon']}")
            else:
                print(f"   [X] No se encontro factura del mes anterior")

            print()

        print("=" * 80)
        print("[OK] Test completado exitosamente")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] Error durante el test: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


def test_automatizacion_completa():
    """
    Prueba el servicio de automatización completo.
    """
    print("\n" + "=" * 80)
    print("TEST: Servicio de Automatización Completo")
    print("=" * 80)
    print()

    db = SessionLocal()

    try:
        # Obtener facturas pendientes (en_revision)
        from app.models.factura import EstadoFactura
        facturas_pendientes = db.query(crud_factura.Factura).filter(
            crud_factura.Factura.estado == EstadoFactura.en_revision
        ).limit(5).all()

        print(f"📋 Facturas pendientes de procesamiento: {len(facturas_pendientes)}")
        print()

        if not facturas_pendientes:
            print("⚠️  No hay facturas pendientes para procesar")
            return

        # Procesar con el servicio de automatización
        automation_service = AutomationService()

        for i, factura in enumerate(facturas_pendientes, 1):
            print(f"--- Procesando Factura {i} ---")
            print(f"   ID: {factura.id}")
            print(f"   Número: {factura.numero_factura}")
            print(f"   Total: ${factura.total_a_pagar:,.2f}")

            try:
                resultado = automation_service.procesar_factura_individual(
                    db=db,
                    factura=factura,
                    modo_debug=True
                )

                print(f"   ✓ Resultado:")
                print(f"      - Decisión: {resultado['decision']}")
                print(f"      - Confianza: {resultado.get('confianza', 0):.2%}")
                print(f"      - Razón: {resultado.get('razon', 'N/A')}")
                print(f"      - Estado nuevo: {resultado.get('estado_nuevo', 'N/A')}")

                if resultado.get('debug_info'):
                    print(f"      - Patrón temporal: {resultado['debug_info']['patron_detallado']['temporal']['tipo']}")

            except Exception as e:
                print(f"   ✗ Error: {str(e)}")

            print()

        print("=" * 80)
        print("✅ Test de automatización completado")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] Error durante el test: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    print("\n>> Iniciando tests del sistema de automatizacion...\n")

    # Test 1: Comparación con mes anterior
    test_comparacion_mes_anterior()

    # Test 2: Servicio de automatización completo
    # test_automatizacion_completa()  # Descomentar cuando esté listo

    print("\n>> Todos los tests completados\n")
