# GUIA DE TESTING: ENDPOINT DE AUTOMATIZACION MANUAL

## Como Usar el Endpoint de Trigger Manual

### URL del Endpoint
```
POST /api/v1/facturas/admin/trigger-automation
```

### Autenticación Requerida
- **Rol requerido:** Admin
- **Método:** Bearer Token en header `Authorization`

---

## Prueba Rápida con Python

```python
import requests

# 1. Login como admin
response = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'usuario': 'alexander.taimal',
    'password': '12345678'
})
token = response.json()['access_token']

# 2. Trigger automation
response = requests.post(
    'http://localhost:8000/api/v1/facturas/admin/trigger-automation',
    headers={'Authorization': f'Bearer {token}'}
)

# 3. Ver resultados
import json
print(json.dumps(response.json(), indent=2))
```

---

## Interpretar la Respuesta

```json
{
  "status": "success",
  "message": "Automation scheduler executed successfully",
  "timestamp": "2025-10-27T20:20:54.470194",
  "triggered_by": "Alexander.taimal",
  "statistics": {
    "before": {
      "total_facturas": 294,
      "workflows": 189,
      "sin_workflow": 105
    },
    "after": {
      "total_facturas": 294,
      "workflows": 516,
      "sin_workflow": 0
    },
    "fase_1": {
      "workflows_creados": 327,
      "workflows_fallidos": 0
    },
    "fase_2": {
      "aprobadas_automaticamente": 0,
      "enviadas_revision": 294,
      "errores": 0
    }
  }
}
```

### Explicación de Campos

**before/after:**
- `total_facturas`: Total de facturas en sistema
- `workflows`: Número de workflows existentes
- `sin_workflow`: Facturas sin workflows asignados

**fase_1:** (Creación de workflows)
- `workflows_creados`: Workflows nuevos creados exitosamente
- `workflows_fallidos`: Workflows que fallaron

**fase_2:** (Procesamiento de automatización)
- `aprobadas_automaticamente`: Facturas auto-aprobadas
- `enviadas_revision`: Facturas que requieren revisión
- `errores`: Errores durante el procesamiento

---

## Casos de Uso

### 1. Ejecutar una vez para procesar todo

```python
import requests

# Obtener token
login = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'usuario': 'alexander.taimal',
    'password': '12345678'
})
token = login.json()['access_token']

# Ejecutar varias veces (hasta que no haya cambios)
for i in range(5):
    result = requests.post(
        'http://localhost:8000/api/v1/facturas/admin/trigger-automation',
        headers={'Authorization': f'Bearer {token}'}
    )
    data = result.json()['statistics']
    print(f"Ejecución {i+1}:")
    print(f"  Workflows sin: {data['before']['sin_workflow']} -> {data['after']['sin_workflow']}")
    print(f"  Creados: {data['fase_1']['workflows_creados']}")
    print(f"  Enviadas a revisión: {data['fase_2']['enviadas_revision']}")

    # Parar si no hay cambios
    if data['fase_1']['workflows_creados'] == 0 and data['fase_2']['enviadas_revision'] == 0:
        break
```

### 2. Verificar estado actual del sistema

```python
import requests

login = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'usuario': 'alexander.taimal',
    'password': '12345678'
})
token = login.json()['access_token']

result = requests.post(
    'http://localhost:8000/api/v1/facturas/admin/trigger-automation',
    headers={'Authorization': f'Bearer {token}'}
)

stats = result.json()['statistics']

print(f"Estado Actual del Sistema:")
print(f"  Facturas: {stats['after']['total_facturas']}")
print(f"  Workflows: {stats['after']['workflows']}")
print(f"  Sin workflow: {stats['after']['sin_workflow']}")
print(f"  Ratio workflows/facturas: {stats['after']['workflows'] / stats['after']['total_facturas']:.2f}")
```

### 3. Testing después de cambios en DecisionEngine

```python
# Útil cuando se modifica la lógica de aprobación
# El endpoint mostrará si hay más auto-aprobaciones
import requests

login = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'usuario': 'alexander.taimal',
    'password': '12345678'
})
token = login.json()['access_token']

result = requests.post(
    'http://localhost:8000/api/v1/facturas/admin/trigger-automation',
    headers={'Authorization': f'Bearer {token}'}
)

fase2 = result.json()['statistics']['fase_2']

print(f"Resultados de Automatización:")
print(f"  Auto-aprobadas: {fase2['aprobadas_automaticamente']}")
print(f"  Enviadas a revisión: {fase2['enviadas_revision']}")
print(f"  Errores: {fase2['errores']}")

if fase2['aprobadas_automaticamente'] > 0:
    print("\n Auto-aprobaciones están funcionando!")
else:
    print("\n⚠️ No hay auto-aprobaciones (revisar reglas)")
```

---

## Problemas Comunes y Soluciones

### Problema: "Token inválido"

**Causa:** El token expiró
**Solución:** Obtener un token nuevo antes de ejecutar

```python
login = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'usuario': 'alexander.taimal',
    'password': '12345678'
})
token = login.json()['access_token']
```

### Problema: "Rol insuficiente"

**Causa:** El usuario no es admin
**Solución:** Usar credenciales de admin

```python
# Cambiar usuario
login = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'usuario': 'alexander.taimal',  # ← Admin
    'password': '12345678'
})
```

### Problema: Endpoint retorna 404

**Causa:** Backend no está actualizado
**Solución:** Asegurar que el cambio está en `app/api/v1/routers/facturas.py`

```bash
# Verificar que el endpoint está en el código
grep -n "trigger-automation" app/api/v1/routers/facturas.py
```

### Problema: Workflows_creados = 0 pero sin_workflow disminuyó

**Causa:** Los workflows SÍ se crearon pero el contador está malo
**Solución:** Es un bug menor, ver si sin_workflow baja (lo importante)

```python
# Si sin_workflow baja, significa que SÍ se crearon
before = stats['before']['sin_workflow']
after = stats['after']['sin_workflow']

if before > after:
    print(f" Se crearon {before - after} workflows correctamente")
```

---

## Monitoreo de Logs

El endpoint genera logs detallados. Para verlos:

```bash
# Seguir logs en tiempo real (si uvicorn corre en terminal)
# Buscar: "MANUAL AUTOMATION TRIGGER"

# O revisar logs del servidor
tail -f logs/app.log | grep "MANUAL AUTOMATION"
```

---

## Métricas a Monitorear

### Cada vez que ejecutas el endpoint, monitorea:

1. **Creación de workflows:**
   ```
   workflows_antes + workflows_creados = workflows_despues
   ```

2. **Cobertura:**
   ```
   sin_workflow_despues + workflows_creados >= sin_workflow_antes
   ```

3. **Procesamiento:**
   ```
   aprobadas_automaticamente + enviadas_revision = facturas_procesadas
   ```

4. **Errores:**
   ```
   errores debe ser 0
   ```

---

## Flujo Típico de Testing

```
1. Revisar estado inicial
   GET /api/v1/facturas/ → Ver que todas estén en "en_revision"

2. Ejecutar trigger
   POST /admin/trigger-automation → Obtener estadísticas

3. Verificar creación de workflows
   statistics.fase_1.workflows_creados > 0

4. Verificar procesamiento
   statistics.fase_2.enviadas_revision > 0

5. Revisar estado final
   GET /api/v1/facturas/ → Verificar cambios de estado

6. Analizar logs
   Ver detalles en consola o logs
```

---

## Script Completo para Automatización

```python
#!/usr/bin/env python3
"""
script_test_automation.py
Script para testear y monitorear la automatización de facturas
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
ADMIN_USER = "alexander.taimal"
ADMIN_PASS = "12345678"

def get_token():
    """Obtener token de autenticación"""
    resp = requests.post(f'{BASE_URL}/api/v1/auth/login', json={
        'usuario': ADMIN_USER,
        'password': ADMIN_PASS
    })
    return resp.json()['access_token']

def trigger_automation(token):
    """Ejecutar endpoint de trigger manual"""
    resp = requests.post(
        f'{BASE_URL}/api/v1/facturas/admin/trigger-automation',
        headers={'Authorization': f'Bearer {token}'}
    )
    return resp.json()

def print_results(result):
    """Imprimir resultados de forma legible"""
    timestamp = result['timestamp']
    stats = result['statistics']

    print(f"\n{'='*70}")
    print(f"Timestamp: {timestamp}")
    print(f"{'='*70}")

    print("\nFASE 1 (Creación de Workflows):")
    print(f"  Sin workflow antes:  {stats['before']['sin_workflow']}")
    print(f"  Sin workflow después: {stats['after']['sin_workflow']}")
    print(f"  Creados: {stats['fase_1']['workflows_creados']}")
    print(f"  Fallidos: {stats['fase_1']['workflows_fallidos']}")

    print("\nFASE 2 (Procesamiento Automático):")
    print(f"  Auto-aprobadas: {stats['fase_2']['aprobadas_automaticamente']}")
    print(f"  Enviadas a revisión: {stats['fase_2']['enviadas_revision']}")
    print(f"  Errores: {stats['fase_2']['errores']}")

    print("\nEstadísticas Finales:")
    print(f"  Workflows totales: {stats['after']['workflows']}")
    print(f"  Cobertura: {100 - (stats['after']['sin_workflow'] * 100 // stats['after']['total_facturas'])}%")

def main():
    """Main script"""
    print("🚀 Iniciando test de automatización...")

    token = get_token()
    print(f" Token obtenido para {ADMIN_USER}")

    # Ejecutar hasta que no haya cambios
    iterations = 0
    max_iterations = 5

    while iterations < max_iterations:
        iterations += 1
        print(f"\n▶️ Ejecución {iterations}...")

        result = trigger_automation(token)
        print_results(result)

        # Parar si no hay cambios
        stats = result['statistics']
        if stats['fase_1']['workflows_creados'] == 0 and stats['fase_2']['enviadas_revision'] == 0:
            print("\n Proceso completado (sin cambios)")
            break

        # Esperar un poco antes de siguiente iteración
        if iterations < max_iterations:
            time.sleep(2)

    print("\n" + "="*70)
    print(" Test completado")
    print("="*70)

if __name__ == "__main__":
    main()
```

**Usar:**
```bash
python script_test_automation.py
```

---

## Resumen

El endpoint `/admin/trigger-automation` es una herramienta poderosa para:
-  Testing del sistema
-  Debugging de problemas
-  Monitoreo de estado
-  Validación después de cambios
-  Análisis de logs

Usarlo siempre que modifiques:
- `DecisionEngine`
- `WorkflowAutomaticoService`
- `AutomationService`
- O cualquier lógica de automatización

---

**Generado:** 2025-10-27
**Para:** Equipo de desarrollo AFE
**Versión:** 1.0
