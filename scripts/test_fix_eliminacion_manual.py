"""
Test manual del fix de soft delete - Simulación del problema original

Este script simula exactamente el problema que reportó el usuario:
1. Crear asignación
2. Eliminarla (con consentimiento)
3. Intentar crear la misma asignación nuevamente

ANTES DEL FIX: Fallaba con "Ya existe en el sistema"
DESPUÉS DEL FIX: Debe funcionar correctamente (reactivación)
"""
import sys
sys.path.insert(0, '.')

import requests
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:5173/api/v1"  # Ajustar según tu configuración
# Para obtener el token, hacer login primero o usar token existente
TOKEN = None  # Se obtendrá mediante login

def login():
    """Login para obtener token de autenticación."""
    global TOKEN

    # Ajustar credenciales según tu sistema
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "usuario": "admin",  # Ajustar
        "password": "admin123"  # Ajustar
    })

    if response.status_code == 200:
        TOKEN = response.json().get("access_token")
        print("  Login exitoso")
        return True
    else:
        print(f" Error en login: {response.status_code}")
        print(f"   Respuesta: {response.text}")
        return False

def get_headers():
    """Obtiene headers con autenticación."""
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

def test_flujo_eliminacion_recreacion():
    """
    Test del flujo completo: crear → eliminar → recrear

    Este es el caso de uso que estaba fallando.
    """
    print("\n" + "=" * 80)
    print("TEST: FLUJO COMPLETO DE ELIMINACIÓN Y RECREACIÓN")
    print("=" * 80)

    # Datos de prueba (usar NIT único para evitar conflictos)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    payload = {
        "nit": f"TEST_{timestamp}",
        "responsable_id": 1,  # Ajustar según tu sistema
        "nombre_proveedor": "TEST Empresa SAS",
        "permitir_aprobacion_automatica": True
    }

    print(f"\nNIT de prueba: {payload['nit']}")

    # PASO 1: Crear asignación
    print("\n1️⃣ PASO 1: Crear asignación...")
    response = requests.post(
        f"{BASE_URL}/asignacion-nit/",
        json=payload,
        headers=get_headers()
    )

    if response.status_code != 201:
        print(f" Error creando asignación: {response.status_code}")
        print(f"   Respuesta: {response.text}")
        return False

    asignacion = response.json()
    asignacion_id = asignacion["id"]
    print(f"  Asignación creada exitosamente (ID: {asignacion_id})")

    # PASO 2: Verificar que aparece en listado
    print("\n2️⃣ PASO 2: Verificar que aparece en listado...")
    response = requests.get(
        f"{BASE_URL}/asignacion-nit/",
        headers=get_headers()
    )

    if response.status_code != 200:
        print(f" Error obteniendo listado: {response.status_code}")
        return False

    asignaciones = response.json()
    existe = any(a["id"] == asignacion_id for a in asignaciones)

    if existe:
        print(f"  Asignación aparece en listado")
    else:
        print(f" Asignación NO aparece en listado")
        return False

    # PASO 3: Eliminar asignación (simula usuario eliminando con consentimiento)
    print("\n3️⃣ PASO 3: Eliminar asignación (soft delete)...")
    response = requests.delete(
        f"{BASE_URL}/asignacion-nit/{asignacion_id}",
        headers=get_headers()
    )

    if response.status_code != 204:
        print(f" Error eliminando asignación: {response.status_code}")
        print(f"   Respuesta: {response.text}")
        return False

    print(f"  Asignación eliminada exitosamente")

    # PASO 4: Verificar que NO aparece en listado
    print("\n4️⃣ PASO 4: Verificar que NO aparece en listado...")
    response = requests.get(
        f"{BASE_URL}/asignacion-nit/",
        headers=get_headers()
    )

    if response.status_code != 200:
        print(f" Error obteniendo listado: {response.status_code}")
        return False

    asignaciones = response.json()
    existe = any(a["id"] == asignacion_id for a in asignaciones)

    if not existe:
        print(f"  Asignación NO aparece en listado (correcto, está eliminada)")
    else:
        print(f" Asignación TODAVÍA aparece en listado (bug no resuelto)")
        return False

    # PASO 5: CRÍTICO - Recrear la misma asignación
    print("\n5️⃣ PASO 5: CRÍTICO - Recrear la misma asignación...")
    print("   (Esto es lo que estaba fallando antes del fix)")

    response = requests.post(
        f"{BASE_URL}/asignacion-nit/",
        json=payload,
        headers=get_headers()
    )

    if response.status_code != 201:
        print(f" ERROR: No se pudo recrear asignación")
        print(f"   Status: {response.status_code}")
        print(f"   Respuesta: {response.text}")
        print("\n  EL BUG NO ESTÁ RESUELTO - El fix no funcionó correctamente")
        return False

    asignacion_recreada = response.json()

    print(f"  Asignación recreada exitosamente!")
    print(f"   ID original: {asignacion_id}")
    print(f"   ID recreado: {asignacion_recreada['id']}")

    if asignacion_recreada['id'] == asignacion_id:
        print(f"     REACTIVACIÓN: Se reutilizó el mismo ID (patrón correcto)")
    else:
        print(f"     NUEVO REGISTRO: Se creó nuevo ID (funciona pero no óptimo)")

    # PASO 6: Verificar que aparece en listado nuevamente
    print("\n6️⃣ PASO 6: Verificar que aparece en listado nuevamente...")
    response = requests.get(
        f"{BASE_URL}/asignacion-nit/",
        headers=get_headers()
    )

    if response.status_code != 200:
        print(f" Error obteniendo listado: {response.status_code}")
        return False

    asignaciones = response.json()
    existe = any(a["nit"] == payload["nit"] for a in asignaciones)

    if existe:
        print(f"  Asignación aparece en listado después de recrear")
    else:
        print(f" Asignación NO aparece en listado después de recrear")
        return False

    # LIMPIEZA: Eliminar asignación de prueba
    print("\n🧹 LIMPIEZA: Eliminando asignación de prueba...")
    requests.delete(
        f"{BASE_URL}/asignacion-nit/{asignacion_recreada['id']}",
        headers=get_headers()
    )

    print("\n" + "=" * 80)
    print("    TEST COMPLETADO EXITOSAMENTE    ")
    print("=" * 80)
    print("\nRESULTADO: El fix de soft delete está funcionando correctamente.")
    print("El usuario puede eliminar y recrear asignaciones sin problemas.")
    print("=" * 80)

    return True

def main():
    """Función principal."""
    print("=" * 80)
    print("TEST MANUAL: Verificación del Fix de Soft Delete")
    print("Proyecto: AFE Backend - Asignaciones NIT-Responsable")
    print("=" * 80)

    # Login
    print("\n🔐 Autenticando...")
    if not login():
        print("\n No se pudo autenticar. Ajuste las credenciales en el script.")
        return 1

    # Ejecutar test
    resultado = test_flujo_eliminacion_recreacion()

    if resultado:
        print("\n🎉 ¡ÉXITO! El sistema está funcionando correctamente.")
        return 0
    else:
        print("\n ERROR: El test falló. Revisar logs para más detalles.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except requests.exceptions.ConnectionError:
        print("\n ERROR: No se pudo conectar al servidor.")
        print("   Verifique que el backend esté corriendo en http://localhost:5173")
        sys.exit(1)
    except Exception as e:
        print(f"\n ERROR INESPERADO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
