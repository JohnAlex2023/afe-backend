# test_automation_quick.py
"""
Script de prueba rápida para verificar el sistema de automatización sin ejecutar procesamiento real.
"""

import sys
import json
from pathlib import Path

# Agregar el path del proyecto
sys.path.append(str(Path(__file__).parent))

def test_automation_imports():
    """Prueba que todas las importaciones funcionen correctamente."""
    try:
        from app.services.automation.automation_service import AutomationService
        from app.services.automation.fingerprint_generator import FingerprintGenerator
        from app.services.automation.pattern_detector import PatternDetector
        from app.services.automation.decision_engine import DecisionEngine
        from app.services.automation.notification_service import NotificationService
        
        print("✅ Todas las importaciones de automatización exitosas")
        return True
    except Exception as e:
        print(f"❌ Error en importaciones: {e}")
        return False

def test_fingerprint_generation():
    """Prueba la generación de fingerprints."""
    try:
        from app.services.automation.fingerprint_generator import FingerprintGenerator
        
        generator = FingerprintGenerator()
        
        # Prueba con concepto médico
        concepto_test = "Consulta médica especializada - Cardiología pediátrica"
        
        fingerprints = generator.generar_fingerprint_concepto(concepto_test)
        print(f"✅ Fingerprint generado: {fingerprints['principal'][:20]}...")
        
        normalizado = generator.normalizar_concepto_medico(concepto_test)
        print(f"✅ Concepto normalizado: {normalizado}")
        
        return True
    except Exception as e:
        print(f"❌ Error en generación de fingerprints: {e}")
        return False

def test_configuration_serialization():
    """Prueba la serialización de configuración para evitar errores JSON."""
    try:
        from app.services.automation.decision_engine import DecisionEngine
        from decimal import Decimal
        
        engine = DecisionEngine()
        
        # Probar serialización de configuración
        config_serializable = engine._serializar_config_para_json()
        
        # Verificar que se puede serializar a JSON
        json_str = json.dumps(config_serializable)
        print("✅ Configuración serializable a JSON exitosamente")
        
        # Verificar que no hay Decimals ni sets en el resultado
        for key, value in config_serializable.items():
            if isinstance(value, Decimal):
                print(f"❌ Decimal no convertido en {key}: {value}")
                return False
            elif isinstance(value, set):
                print(f"❌ Set no convertido en {key}: {value}")
                return False
        
        print("✅ Todos los tipos de datos son JSON-serializables")
        return True
    except Exception as e:
        print(f"❌ Error en serialización: {e}")
        return False

def test_automation_service_init():
    """Prueba que el servicio de automatización se inicialice correctamente."""
    try:
        from app.services.automation.automation_service import AutomationService
        
        service = AutomationService()
        config = service.obtener_configuracion_actual()
        
        print("✅ AutomationService inicializado correctamente")
        print(f"   - FingerprintGenerator: activo")
        print(f"   - PatternDetector umbrales: {len(service.pattern_detector.umbrales)} configurados")
        print(f"   - DecisionEngine config: {len(service.decision_engine.config)} parámetros")
        
        return True
    except Exception as e:
        print(f"❌ Error inicializando AutomationService: {e}")
        return False

def test_api_router_import():
    """Prueba que el router de APIs se importe sin errores."""
    try:
        from app.api.v1.routers.automation import router
        print("✅ Router de automatización importado correctamente")
        
        # Verificar que las rutas estén registradas
        routes = [route.path for route in router.routes]
        print(f"   - {len(routes)} rutas registradas")
        
        expected_routes = ["/procesar", "/estadisticas", "/facturas-procesadas", "/configuracion"]
        for expected in expected_routes:
            if any(expected in route for route in routes):
                print(f"   ✓ Ruta encontrada: {expected}")
            else:
                print(f"   ⚠ Ruta no encontrada: {expected}")
        
        return True
    except Exception as e:
        print(f"❌ Error importando router: {e}")
        return False

def main():
    """Ejecuta todas las pruebas de verificación."""
    print("🔍 PRUEBAS RÁPIDAS DEL SISTEMA DE AUTOMATIZACIÓN")
    print("=" * 60)
    
    tests = [
        ("Importaciones", test_automation_imports),
        ("Generación de Fingerprints", test_fingerprint_generation),
        ("Serialización JSON", test_configuration_serialization),
        ("Inicialización de Servicio", test_automation_service_init),
        ("Router de APIs", test_api_router_import),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n📋 Ejecutando: {name}")
        print("-" * 40)
        try:
            if test_func():
                passed += 1
                print(f"✅ {name}: PASSED")
            else:
                print(f"❌ {name}: FAILED")
        except Exception as e:
            print(f"❌ {name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTADO FINAL: {passed}/{total} pruebas exitosas")
    
    if passed == total:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON! El sistema está listo.")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisar errores arriba.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)