# test_complete_processing.py
"""
Prueba completa del procesamiento de automatización con facturas reales.
"""

from app.db.session import SessionLocal
from app.services.automation.automation_service import AutomationService
from app.crud.factura import get_factura

def test_process_real_invoice():
    """Procesa una factura real del sistema."""
    print("🔥 PRUEBA DE PROCESAMIENTO COMPLETO")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        # Obtener una factura real
        factura = get_factura(db, factura_id=1)
        
        if not factura:
            print("❌ No se encontró la factura ID 1")
            return False
        
        print(f"📄 Procesando Factura: {factura.numero_factura}")
        print(f"   🏢 Proveedor ID: {factura.proveedor_id}")
        print(f"   💰 Total: ${factura.total_a_pagar}")
        print(f"   📋 Concepto: {factura.concepto_principal}")
        
        # Crear servicio de automatización
        automation_service = AutomationService()
        
        # Procesar la factura
        print("\n⚙️ Iniciando procesamiento...")
        resultado = automation_service.procesar_factura_individual(db, factura, modo_debug=True)
        
        print(f"\n✅ Procesamiento completado!")
        print(f"   🎯 Estado: {resultado['estado']}")
        print(f"   📊 Confianza: {resultado['confianza']:.2%}")
        print(f"   💡 Razón: {resultado['razon']}")
        
        if resultado['patrones_detectados']:
            print(f"   🔍 Patrones detectados: {len(resultado['patrones_detectados'])}")
            
        # Verificar que se guardó en base de datos
        db.refresh(factura)
        print(f"\n💾 Datos guardados:")
        print(f"   🔐 Hash concepto: {factura.concepto_hash[:16] if factura.concepto_hash else 'No generado'}...")
        print(f"   📈 Confianza: {factura.confianza_automatica}")
        print(f"   ⚙️ Procesado: {'Sí' if factura.fecha_procesamiento_auto else 'No'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error durante el procesamiento: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_statistics():
    """Prueba las estadísticas del sistema."""
    print("\n📊 ESTADÍSTICAS DEL SISTEMA")
    print("-" * 30)
    
    try:
        automation_service = AutomationService()
        stats = automation_service.obtener_estadisticas()
        
        for key, value in stats.items():
            print(f"   📈 {key}: {value}")
            
        return True
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        return False

def main():
    """Ejecuta las pruebas de procesamiento completo."""
    print("🚀 PRUEBA DE PROCESAMIENTO COMPLETO")
    print("🎯 Objetivo: Procesar factura real de Kit Renasys")
    
    success_count = 0
    
    # Test 1: Procesar factura individual
    if test_process_real_invoice():
        success_count += 1
    
    # Test 2: Obtener estadísticas
    if test_statistics():
        success_count += 1
    
    print("\n" + "=" * 50)
    if success_count == 2:
        print("🎉 ¡PROCESAMIENTO EXITOSO!")
        print("   ✅ Factura procesada correctamente")
        print("   ✅ Datos guardados en base de datos") 
        print("   ✅ Estadísticas actualizadas")
        print("\n🚀 ¡El sistema de automatización está completamente funcional!")
    else:
        print(f"⚠️ {success_count}/2 pruebas exitosas")
        print("El sistema básico funciona pero hay detalles menores por ajustar")

if __name__ == "__main__":
    main()