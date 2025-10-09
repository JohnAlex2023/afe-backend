# 🤖 Sistema de Aprobación Automática - Comparación Mes Anterior

## 📋 Resumen Ejecutivo

Se ha implementado un sistema de automatización de aprobación de facturas que compara la factura del mes actual con la del mes anterior del mismo proveedor y concepto. Si el monto es igual o similar (dentro de una tolerancia configurable), la factura se aprueba automáticamente.

### ✨ Características Principales

- ✅ **Comparación inteligente**: Busca facturas del mismo proveedor y concepto del mes anterior
- ✅ **Tolerancia configurable**: Por defecto 5% de diferencia permitida
- ✅ **Confianza graduada**: Mayor confianza para montos idénticos, menor para diferencias pequeñas
- ✅ **Auditoría completa**: Todas las decisiones quedan registradas con explicación
- ✅ **API REST completa**: Endpoints para ejecutar, configurar y monitorear
- ✅ **Modo debug**: Información detallada para análisis y troubleshooting

---

## 🏗️ Arquitectura de la Solución

### 1. **Capa CRUD** (`app/crud/factura.py`)

#### Función: `find_factura_mes_anterior()`
Busca la factura del mes anterior del mismo proveedor.

```python
factura_anterior = find_factura_mes_anterior(
    db=db,
    proveedor_id=3,
    fecha_actual=date(2025, 10, 1),
    concepto_hash="abc123",
    concepto_normalizado="Servicios de mantenimiento"
)
```

**Estrategia de búsqueda:**
1. Calcula mes anterior (ej: si actual es 2025-10, busca 2025-09)
2. Busca facturas del mismo proveedor en ese periodo
3. Filtra por concepto (hash preferido, luego normalizado)
4. Solo considera facturas aprobadas
5. Retorna la más reciente

#### Función: `find_facturas_mismo_concepto_ultimos_meses()`
Busca facturas similares en los últimos N meses para análisis de patrones.

---

### 2. **Capa de Detección de Patrones** (`app/services/automation/pattern_detector.py`)

#### Método: `comparar_con_mes_anterior()`

```python
comparacion = pattern_detector.comparar_con_mes_anterior(
    factura_nueva=factura_actual,
    factura_mes_anterior=factura_sept,
    tolerancia_porcentaje=5.0
)
```

**Retorna:**
```json
{
    "tiene_mes_anterior": true,
    "montos_coinciden": true,
    "diferencia_porcentaje": 2.5,
    "diferencia_absoluta": 50000,
    "decision_sugerida": "aprobar_auto",
    "razon": "Monto similar al mes anterior: $2,000,000 → $2,050,000 (2.5% diferencia)",
    "confianza": 0.85,
    "monto_actual": 2050000,
    "monto_anterior": 2000000,
    "factura_anterior_id": 123,
    "factura_anterior_numero": "FACT-SEP-001"
}
```

**Niveles de confianza:**
- 0% diferencia = 100% confianza
- ≤1% diferencia = 95% confianza
- ≤3% diferencia = 85% confianza
- ≤5% diferencia = 75% confianza
- ≤10% diferencia = 60% confianza
- >10% diferencia = 40% confianza

---

### 3. **Motor de Decisiones** (`app/services/automation/decision_engine.py`)

#### Lógica de Decisión

```
┌─────────────────────────────────────────┐
│  ¿Existe factura del mes anterior?      │
└─────────────┬───────────────────────────┘
              │
        ┌─────┴─────┐
        │    SI     │
        └─────┬─────┘
              │
    ┌─────────┴──────────┐
    │ Diferencia ≤ 5%?   │
    └─────┬──────────────┘
          │
     ┌────┴────┐
     │   SI    │         ✅ APROBACIÓN AUTOMÁTICA
     └─────────┘         Confianza: 75-100%
          │
     ┌────┴────┐
     │   NO    │         ⚠️ REVISIÓN MANUAL
     └─────────┘         Diferencia supera tolerancia
```

**Prioridad máxima:**
Si hay coincidencia con mes anterior, esta decisión tiene prioridad sobre todos los demás criterios del sistema.

---

### 4. **Servicio de Automatización** (`app/services/automation/automation_service.py`)

#### Flujo de procesamiento:

```python
automation_service = AutomationService()

# Procesar facturas pendientes
resultado = automation_service.procesar_facturas_pendientes(
    db=db,
    limite_facturas=50,
    modo_debug=False
)
```

**Proceso por factura:**
1. ✅ Validar datos mínimos
2. 🔍 Buscar factura del mes anterior (PRIORIDAD 1)
3. 📊 Comparar montos
4. 🎯 Tomar decisión
5. 💾 Aplicar decisión a BD
6. 📝 Registrar en auditoría

---

## 🌐 API Endpoints

### Base URL: `/api/v1/automatizacion/`

### 1. **Procesar Facturas Automáticamente**

```http
POST /automatizacion/procesar
Content-Type: application/json

{
    "tolerancia_porcentaje": 5.0,
    "limite_facturas": 50,
    "modo_debug": false
}
```

**Respuesta:**
```json
{
    "success": true,
    "message": "Procesadas 45 facturas. 12 aprobadas automáticamente, 33 enviadas a revisión.",
    "data": {
        "facturas_procesadas": 45,
        "aprobadas_automaticamente": 12,
        "enviadas_revision": 33,
        "errores": 0,
        "tasa_automatizacion": 26.67,
        "tiempo_procesamiento_segundos": 3.45
    }
}
```

---

### 2. **Listar Facturas Pendientes**

```http
GET /automatizacion/facturas-pendientes?limite=100
```

**Respuesta:**
```json
{
    "success": true,
    "message": "25 facturas pendientes de procesamiento",
    "data": {
        "total": 25,
        "facturas": [
            {
                "id": 150,
                "numero_factura": "FACT-OCT-001",
                "fecha_emision": "2025-10-05",
                "total": 2500000,
                "proveedor_nombre": "Servicios SA",
                "tiene_mes_anterior": true,
                "mes_anterior": {
                    "id": 125,
                    "numero": "FACT-SEP-001",
                    "total": 2500000,
                    "diferencia_porcentaje": 0.0,
                    "aprobacion_estimada": "SI"
                }
            }
        ]
    }
}
```

---

### 3. **Procesar Factura Individual**

```http
POST /automatizacion/procesar-factura/150?modo_debug=true
```

**Respuesta:**
```json
{
    "success": true,
    "message": "Factura procesada: aprobada_auto",
    "data": {
        "factura_id": 150,
        "numero_factura": "FACT-OCT-001",
        "decision": "aprobada_auto",
        "confianza": 1.0,
        "razon": "Monto idéntico al mes anterior ($2,500,000.00)",
        "estado_nuevo": "aprobada_auto",
        "debug_info": {
            "comparacion_detalle": {
                "tiene_mes_anterior": true,
                "diferencia_porcentaje": 0.0,
                "factura_anterior_id": 125
            }
        }
    }
}
```

---

### 4. **Estadísticas de Automatización**

```http
GET /automatizacion/estadisticas?dias=30
```

**Respuesta:**
```json
{
    "success": true,
    "message": "Estadísticas de 30 días",
    "data": {
        "periodo": {
            "desde": "2025-09-08",
            "hasta": "2025-10-08",
            "dias": 30
        },
        "totales": {
            "procesadas": 150,
            "aprobadas_auto": 45,
            "enviadas_revision": 105,
            "tasa_automatizacion": 30.0
        },
        "por_metodo": {
            "comparacion_mes_anterior": 42,
            "patron_recurrencia": 3
        }
    }
}
```

---

## 🚀 Guía de Uso

### Opción 1: Desde Python/Script

```python
from app.services.automation.automation_service import AutomationService
from app.db.session import SessionLocal

db = SessionLocal()
service = AutomationService()

# Procesar facturas
resultado = service.procesar_facturas_pendientes(
    db=db,
    limite_facturas=50,
    modo_debug=True
)

print(f"Procesadas: {resultado['facturas_procesadas']}")
print(f"Aprobadas auto: {resultado['aprobadas_automaticamente']}")
print(f"Tasa: {resultado['resumen_general']['tasa_automatizacion']}%")
```

### Opción 2: Desde API REST

```bash
# 1. Ver facturas pendientes
curl -X GET "http://localhost:8000/api/v1/automatizacion/facturas-pendientes?limite=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 2. Procesar todas las pendientes
curl -X POST "http://localhost:8000/api/v1/automatizacion/procesar" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tolerancia_porcentaje": 5.0,
    "limite_facturas": 50,
    "modo_debug": false
  }'

# 3. Procesar una factura específica (testing)
curl -X POST "http://localhost:8000/api/v1/automatizacion/procesar-factura/150?modo_debug=true" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. Ver estadísticas
curl -X GET "http://localhost:8000/api/v1/automatizacion/estadisticas?dias=30" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Opción 3: Desde Script de Test

```bash
# Ejecutar test de comparación
python test_automatizacion_mes_anterior.py
```

---

## ⚙️ Configuración

### Tolerancia de Diferencia

La tolerancia por defecto es **5%**. Para cambiar:

**Opción 1: Por API**
```json
POST /automatizacion/procesar
{
    "tolerancia_porcentaje": 10.0  // 10% de tolerancia
}
```

**Opción 2: En código**
```python
# En automation_service.py línea 149
comparacion_mes_anterior = self.pattern_detector.comparar_con_mes_anterior(
    factura_nueva=factura,
    factura_mes_anterior=factura_mes_anterior,
    tolerancia_porcentaje=10.0  # Cambiar aquí
)
```

---

## 📊 Casos de Uso

### Caso 1: Factura Recurrente Mensual (IDEAL)

```
Proveedor: Servicios de Internet SA
Concepto: Internet empresarial 100MB

Septiembre 2025: $500,000
Octubre 2025: $500,000

✅ Diferencia: 0%
✅ Decisión: APROBACIÓN AUTOMÁTICA
✅ Confianza: 100%
```

### Caso 2: Factura con Variación Pequeña (OK)

```
Proveedor: Energía Eléctrica SA
Concepto: Consumo eléctrico

Septiembre 2025: $1,000,000
Octubre 2025: $1,030,000

✅ Diferencia: 3%
✅ Decisión: APROBACIÓN AUTOMÁTICA
✅ Confianza: 85%
```

### Caso 3: Factura con Variación Grande (REVISIÓN)

```
Proveedor: Papelería SA
Concepto: Suministros de oficina

Septiembre 2025: $200,000
Octubre 2025: $350,000

❌ Diferencia: 75%
⚠️ Decisión: REVISIÓN MANUAL
⚠️ Razón: Monto difiere significativamente del mes anterior
```

### Caso 4: Primera Vez (REVISIÓN)

```
Proveedor: Nuevo Proveedor SA
Concepto: Servicios de consultoría

Septiembre 2025: (no existe)
Octubre 2025: $5,000,000

⚠️ Decisión: REVISIÓN MANUAL
⚠️ Razón: No existe factura del mes anterior para comparar
```

---

## 🔍 Auditoría y Trazabilidad

Cada decisión automática queda registrada con:

- ✅ Decisión tomada (aprobada_auto / en_revision)
- ✅ Nivel de confianza (0-100%)
- ✅ Motivo detallado de la decisión
- ✅ Referencia a factura del mes anterior
- ✅ Diferencia de monto calculada
- ✅ Timestamp de procesamiento
- ✅ Versión del algoritmo utilizado

**Consultar en base de datos:**
```sql
SELECT
    numero_factura,
    estado,
    confianza_automatica,
    motivo_decision,
    factura_referencia_id,
    fecha_procesamiento_auto
FROM facturas
WHERE aprobada_automaticamente = true
ORDER BY fecha_procesamiento_auto DESC;
```

---

## 🛡️ Seguridad y Validaciones

### Validaciones Implementadas

1. ✅ **Permisos**: Solo administradores pueden ejecutar automatización
2. ✅ **Límites**: Máximo 500 facturas por ejecución
3. ✅ **Tolerancia**: Entre 0% y 100%
4. ✅ **Estados**: Solo procesa facturas en 'en_revision' o 'pendiente'
5. ✅ **Referencia**: Solo compara con facturas APROBADAS del mes anterior
6. ✅ **Fecha**: Validación de periodo del mes anterior
7. ✅ **Montos**: Validación de montos válidos (> 0)

---

## 📈 Métricas de Rendimiento

### Velocidad de Procesamiento
- ~100-200ms por factura (con consultas a BD)
- ~50 facturas en ~5-10 segundos
- Optimización con índices en año_factura, mes_factura

### Tasa de Automatización Esperada
- **Facturas recurrentes mensuales**: 80-95%
- **Facturas con pequeñas variaciones**: 50-70%
- **Facturas nuevas/irregulares**: 0-10%

---

## 🔧 Troubleshooting

### Problema: No se encuentran facturas del mes anterior

**Causas posibles:**
1. Proveedor nuevo (primera factura)
2. Concepto diferente mes a mes
3. Facturas del mes anterior no aprobadas

**Solución:**
- Verificar con query SQL:
```sql
SELECT * FROM facturas
WHERE proveedor_id = ?
AND año_factura = ?
AND mes_factura = ?
AND estado IN ('aprobada', 'aprobada_auto');
```

### Problema: Muchas facturas enviadas a revisión

**Causa:** Tolerancia muy baja

**Solución:**
- Aumentar tolerancia a 10% o 15%
- Revisar variabilidad de proveedores

### Problema: Error al procesar

**Solución:**
- Activar `modo_debug=true`
- Revisar logs de auditoría
- Verificar que facturas tengan `concepto_hash` o `concepto_normalizado`

---

## 📝 Próximos Pasos / Mejoras Futuras

1. ⭐ **Dashboard Web**: Interfaz visual para monitoreo
2. ⭐ **Tolerancia por proveedor**: Diferentes % según proveedor
3. ⭐ **Machine Learning**: Predicción de montos basada en histórico
4. ⭐ **Notificaciones**: Alertas cuando automatización es baja
5. ⭐ **Reportes Excel**: Exportar decisiones automáticas
6. ⭐ **Aprobación batch**: Aprobar múltiples facturas con un clic

---

## 📚 Referencias

- **Código fuente**: `app/services/automation/`
- **Tests**: `test_automatizacion_mes_anterior.py`
- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Modelos**: `app/models/factura.py`

---

## ✅ Checklist de Implementación

- [x] Función de búsqueda mes anterior (CRUD)
- [x] Lógica de comparación de montos
- [x] Motor de decisiones actualizado
- [x] Servicio de automatización integrado
- [x] Endpoints API REST
- [x] Tests de funcionalidad
- [x] Auditoría completa
- [x] Documentación

---

**Versión**: 1.0
**Fecha**: 2025-10-08
**Autor**: Sistema de Automatización AFE
