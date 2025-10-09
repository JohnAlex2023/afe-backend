"""
Script de Prueba - Flujo Completo de Automatización

Este script ejecuta el flujo completo de automatización para verificar
que todo el sistema funcione correctamente.

Uso:
    python test_flujo_automatizacion.py
"""

import sys
from datetime import datetime
from app.db.session import SessionLocal
from app.services.flujo_automatizacion_facturas import FlujoAutomatizacionFacturas
from app.models.factura import Factura, EstadoFactura


def main():
    print("=" * 80)
    print("SCRIPT DE PRUEBA - FLUJO DE AUTOMATIZACIÓN")
    print("=" * 80)

    db = SessionLocal()

    try:
        # 1. Verificar facturas existentes
        print("\n📊 PASO 1: Verificación de facturas en BD")
        print("-" * 80)

        total_facturas = db.query(Factura).count()
        print(f"   Total de facturas en BD: {total_facturas}")

        # Contar por estado
        for estado in EstadoFactura:
            count = db.query(Factura).filter(Factura.estado == estado).count()
            print(f"   {estado.value}: {count}")

        if total_facturas == 0:
            print("\n   ⚠️  No hay facturas en la BD. Por favor carga algunas facturas primero.")
            return

        # 2. Ejecutar flujo completo
        print("\n🚀 PASO 2: Ejecutar flujo completo de automatización")
        print("-" * 80)

        flujo = FlujoAutomatizacionFacturas(db)

        # Obtener período actual
        periodo_actual = datetime.now().strftime('%Y-%m')
        print(f"   Período de análisis: {periodo_actual}")

        # Ejecutar flujo
        resultado = flujo.ejecutar_flujo_automatizacion_completo(
            periodo_analisis=periodo_actual
        )

        # 3. Mostrar resultados
        print("\n✅ PASO 3: Resultados del flujo")
        print("-" * 80)

        if resultado['exito']:
            print("   ✅ Flujo ejecutado exitosamente")

            # Mostrar resumen
            resumen = resultado.get('resumen', {})
            stats = resumen.get('estadisticas', {})

            print(f"\n   📈 ESTADÍSTICAS:")
            print(f"   - Facturas marcadas como pagadas: {stats.get('facturas_marcadas_pagadas', 0)}")
            print(f"   - Facturas pendientes analizadas: {stats.get('facturas_pendientes_analizadas', 0)}")
            print(f"   - Facturas aprobadas automáticamente: {stats.get('facturas_aprobadas_auto', 0)}")
            print(f"   - Facturas que requieren revisión: {stats.get('facturas_requieren_revision', 0)}")
            print(f"   - Notificaciones enviadas: {stats.get('notificaciones_enviadas', 0)}")
            print(f"   - Errores: {stats.get('errores', 0)}")
            print(f"   - Tasa de automatización: {resumen.get('tasa_automatizacion', 0):.2f}%")

            # Mostrar detalles de cada paso
            print(f"\n   📋 DETALLES POR PASO:")
            for paso in resultado.get('pasos_completados', []):
                nombre_paso = paso.get('paso', 'Desconocido')
                print(f"\n   {nombre_paso.upper()}")

                if nombre_paso == 'comparacion_aprobacion':
                    resultado_comp = paso.get('resultado', {})
                    print(f"   - Facturas analizadas: {resultado_comp.get('facturas_analizadas', 0)}")
                    print(f"   - Aprobadas automáticamente: {resultado_comp.get('total_aprobadas', 0)}")
                    print(f"   - Requieren revisión: {resultado_comp.get('total_revision', 0)}")

                    # Mostrar algunas aprobadas
                    aprobadas = resultado_comp.get('aprobadas_automaticamente', [])
                    if aprobadas:
                        print(f"\n   ✅ Facturas aprobadas automáticamente (primeras 5):")
                        for i, factura in enumerate(aprobadas[:5], 1):
                            print(f"      {i}. {factura.get('numero_factura')} - {factura.get('proveedor')} - ${factura.get('monto_actual', 0):,.2f}")
                            print(f"         Motivo: {factura.get('motivo')}")

                    # Mostrar algunas en revisión
                    revision = resultado_comp.get('requieren_revision', [])
                    if revision:
                        print(f"\n   ⚠️  Facturas que requieren revisión (primeras 5):")
                        for i, factura in enumerate(revision[:5], 1):
                            print(f"      {i}. {factura.get('numero_factura')} - {factura.get('proveedor')} - ${factura.get('monto_actual', 0):,.2f}")
                            print(f"         Motivo: {factura.get('motivo')}")

        else:
            print("   ❌ Error en la ejecución del flujo")

        # 4. Verificar estado final de facturas
        print("\n📊 PASO 4: Estado final de facturas")
        print("-" * 80)

        for estado in EstadoFactura:
            count = db.query(Factura).filter(Factura.estado == estado).count()
            print(f"   {estado.value}: {count}")

        print("\n" + "=" * 80)
        print("PRUEBA COMPLETADA")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error durante la prueba: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    main()
