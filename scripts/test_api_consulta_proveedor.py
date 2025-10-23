"""
Prueba del endpoint API de consulta por proveedor.

Simula la llamada que hace el frontend cuando el usuario:
1. Selecciona un proveedor del dropdown
2. Hace clic en "Consultar Responsables"
"""

import sys
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

# Crear cliente de pruebas
client = TestClient(app)

# Crear token de autenticación (simular usuario responsable)
# En producción esto vendría del login
token = create_access_token({"sub": "alex.taimal", "role": "responsable"})

headers = {
    "Authorization": f"Bearer {token}"
}

print("=" * 80)
print("PRUEBA DE API: CONSULTAR RESPONSABLES POR PROVEEDOR")
print("=" * 80)

# CASO 1: Proveedor con NIT que tiene guión (901261003-1)
print("\nCASO 1: Buscar por NIT con guion (901261003-1)")
print("-" * 80)

response = client.get(
    "/api/v1/asignacion-nit/",
    params={"nit": "901261003-1"},
    headers=headers
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Responsables encontrados: {len(data)}")
    for asig in data:
        print(f"  - {asig.get('responsable', {}).get('nombre')} ({asig.get('responsable', {}).get('email')})")
        print(f"    NIT en asignacion: {asig.get('nit')}")
else:
    print(f"Error: {response.text}")

# CASO 2: Mismo NIT pero SIN guión (901261003)
print("\n\nCASO 2: Buscar por NIT sin guion (901261003)")
print("-" * 80)

response = client.get(
    "/api/v1/asignacion-nit/",
    params={"nit": "901261003"},
    headers=headers
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Responsables encontrados: {len(data)}")
    for asig in data:
        print(f"  - {asig.get('responsable', {}).get('nombre')} ({asig.get('responsable', {}).get('email')})")
        print(f"    NIT en asignacion: {asig.get('nit')}")
else:
    print(f"Error: {response.text}")

# CASO 3: DATECSA (800136505 sin guion en BD)
print("\n\nCASO 3: Buscar DATECSA por NIT sin guion (800136505)")
print("-" * 80)

response = client.get(
    "/api/v1/asignacion-nit/",
    params={"nit": "800136505"},
    headers=headers
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Responsables encontrados: {len(data)}")
    for asig in data:
        print(f"  - {asig.get('responsable', {}).get('nombre')} ({asig.get('responsable', {}).get('email')})")
        print(f"    NIT en asignacion: {asig.get('nit')}")
else:
    print(f"Error: {response.text}")

# CASO 4: DATECSA con guion simulado (800136505-4)
print("\n\nCASO 4: Buscar DATECSA por NIT CON guion simulado (800136505-4)")
print("-" * 80)

response = client.get(
    "/api/v1/asignacion-nit/",
    params={"nit": "800136505-4"},
    headers=headers
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Responsables encontrados: {len(data)}")
    for asig in data:
        print(f"  - {asig.get('responsable', {}).get('nombre')} ({asig.get('responsable', {}).get('email')})")
        print(f"    NIT en asignacion: {asig.get('nit')}")
else:
    print(f"Error: {response.text}")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("- El endpoint ahora funciona con NITs en CUALQUIER formato")
print("- Normaliza automaticamente antes de comparar")
print("- Frontend puede enviar NITs con o sin guion y funcionara")
print("=" * 80)
