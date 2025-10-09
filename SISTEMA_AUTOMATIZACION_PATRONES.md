# Sistema de Automatización de Facturas Basado en Patrones Históricos

**Nivel:** Enterprise Fortune 500
**Fecha:** 2025-10-08
**Versión:** 2.0
**Autor:** Sistema de Automatización AFE

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Componentes Principales](#componentes-principales)
4. [Flujo de Operación](#flujo-de-operación)
5. [Guía de Implementación](#guía-de-implementación)
6. [API Endpoints](#api-endpoints)
7. [Configuración y Mantenimiento](#configuración-y-mantenimiento)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Resumen Ejecutivo

El Sistema de Automatización de Facturas es una solución enterprise que:

- **Analiza patrones históricos** de facturas pagadas
- **Clasifica automáticamente** en TIPO_A (fijo), TIPO_B (fluctuante), TIPO_C (excepcional)
- **Auto-aprueba facturas recurrentes** con alta confianza (>85%)
- **Reduce tiempo de aprobación** en un 60-80% para facturas recurrentes

### Beneficios Clave

✅ **Automatización inteligente:** Auto-aprobación de facturas recurrentes predecibles
✅ **Aprendizaje continuo:** El sistema mejora con cada factura procesada
✅ **Auditoría completa:** Tracking de todas las decisiones automáticas
✅ **Escalable:** Maneja miles de facturas mensuales sin degradación

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 1: BOOTSTRAP INICIAL                     │
└─────────────────────────────────────────────────────────────────┘

Excel (Facturas pagadas 2025)
    ↓
[importar_historial_excel.py] (ONE-TIME)
    ├─> Agrupa por proveedor + concepto
    ├─> Calcula estadísticas (μ, σ, CV%)
    ├─> Clasifica en TIPO_A/B/C
    └─> Inserta en: historial_pagos

┌─────────────────────────────────────────────────────────────────┐
│                  FASE 2: OPERACIÓN CONTINUA                      │
└─────────────────────────────────────────────────────────────────┘

invoice_extractor (correo) → facturas (BD)
    ↓
[analisis_patrones_service.py] (SCHEDULED - Diario)
    ├─> Query: facturas últimos 3-12 meses
    ├─> Agrupa por proveedor + concepto
    ├─> Calcula estadísticas actualizadas
    └─> UPDATE/INSERT: historial_pagos

    ↓
[automation_service.py] (REAL-TIME - Al extraer factura)
    ├─> Consulta: historial_pagos (patrón vigente)
    ├─> [historial_integration.py] Ajusta score según TIPO
    ├─> [decision_engine.py] Evalúa criterios
    └─> Decide: AUTO-APROBADA / REVISIÓN_MANUAL
```

---

## 🔧 Componentes Principales

### 1. **Modelo de Datos: `historial_pagos`**

Tabla central que almacena patrones históricos de pago.

**Campos principales:**
- `proveedor_id`: FK a proveedores
- `concepto_normalizado`: Concepto limpio para matching
- `concepto_hash`: MD5 para búsqueda rápida
- `tipo_patron`: ENUM (TIPO_A, TIPO_B, TIPO_C)
- `monto_promedio`, `desviacion_estandar`, `coeficiente_variacion`
- `puede_aprobar_auto`: Boolean para auto-aprobación
- `umbral_alerta`: % de desviación para alertas

**Clasificación de Patrones:**

| Tipo | CV% | Descripción | Ejemplo | Auto-aprobar |
|------|-----|-------------|---------|--------------|
| TIPO_A | <5% | Valores fijos | Licencias mensuales | ✅ Sí (alta confianza) |
| TIPO_B | <30% | Fluctuantes predecibles | Servicios cloud variables | ⚠️ Condicional |
| TIPO_C | >30% | Excepcionales | Proyectos únicos | ❌ No |

---

### 2. **Script Bootstrap: `importar_historial_excel.py`**

**Propósito:** Importación ONE-TIME del Excel con historial 2025.

**Uso:**
```bash
python -m app.scripts.importar_historial_excel
```

**Configuración:**
```python
ARCHIVO_CSV = r"C:\ruta\al\archivo.csv"
AÑO_ANALISIS = 2025
SOLO_ULTIMOS_MESES = None  # None = todos, 3 = últimos 3
```

**Output esperado:**
```
================================================================================
IMPORTACIÓN DE HISTORIAL DE FACTURAS - BOOTSTRAP INICIAL
================================================================================
✅ 450 filas cargadas
✅ 120 líneas de gasto extraídas
✅ 85 patrones únicos detectados
✅ Creados: 82 | Actualizados: 3

Total patrones detectados: 85
└─ TIPO_A (Fijo, CV<5%): 42
└─ TIPO_B (Fluctuante, CV<30%): 31
└─ TIPO_C (Excepcional, CV>30%): 12

🤖 Patrones auto-aprobables: 68 (80.0%)
```

---

### 3. **Servicio de Producción: `analisis_patrones_service.py`**

**Propósito:** Análisis continuo desde facturas BD.

**Uso programático:**
```python
from app.services.analisis_patrones_service import AnalizadorPatronesService

db = SessionLocal()
analizador = AnalizadorPatronesService(db)

resultado = analizador.analizar_patrones_desde_bd(
    ventana_meses=12,
    solo_proveedores=[1, 2, 3],  # Opcional
    forzar_recalculo=False
)

print(f"Patrones nuevos: {resultado['estadisticas']['patrones_nuevos']}")
print(f"Patrones actualizados: {resultado['estadisticas']['patrones_actualizados']}")
```

**Características:**
- ✅ Detección automática de cambios significativos
- ✅ No actualiza si no hay cambios (optimizado)
- ✅ Tracking de mejoras/degradaciones de patrones
- ✅ Análisis de frecuencia temporal (mensual, quincenal, etc.)

---

### 4. **Integración con Automatización: `historial_integration.py`**

**Propósito:** Helper para integrar historial_pagos con automation_service.

**Funciones principales:**

#### `buscar_patron_historico(db, factura)`
Busca patrón histórico que coincida con la factura.

```python
from app.services.automation.historial_integration import HistorialIntegrationHelper

patron = HistorialIntegrationHelper.buscar_patron_historico(db, factura)

if patron:
    print(f"Patrón encontrado: {patron.tipo_patron.value}")
    print(f"Monto promedio: ${patron.monto_promedio:,.2f}")
```

#### `calcular_ajuste_confianza(patron, monto)`
Ajusta score de confianza según tipo de patrón.

```python
ajuste = HistorialIntegrationHelper.calcular_ajuste_confianza(
    patron_historico=patron,
    monto_factura=Decimal('5000000')
)

print(f"Ajuste: {ajuste['ajuste_confianza']:.0%}")
print(f"Razón: {ajuste['razon']}")
# Output:
# Ajuste: +30%
# Razón: TIPO_A: Monto dentro del rango esperado (±15%), variación: 2.3%
```

**Reglas de Ajuste:**

| Tipo Patrón | Condición | Ajuste Confianza |
|-------------|-----------|------------------|
| TIPO_A | Monto dentro de ±15% | +30% |
| TIPO_A | Monto fuera de ±15% | -10% + revisión manual |
| TIPO_B | Dentro rango (μ ± 2σ) | +20% |
| TIPO_B | Fuera de rango | -5% + revisión manual |
| TIPO_C | Siempre | -20% + revisión manual |

---

## 🔄 Flujo de Operación

### Flujo Completo: Desde Correo hasta Auto-Aprobación

```
1. invoice_extractor extrae factura del correo
   └─> Inserta en tabla: facturas (estado=pendiente)

2. automation_service.procesar_factura_individual()
   ├─> 2.1. Validar datos mínimos
   ├─> 2.2. Buscar patrón en historial_pagos
   ├─> 2.3. Buscar facturas históricas similares (BD)
   ├─> 2.4. Analizar patrón de recurrencia
   └─> 2.5. Tomar decisión

3. decision_engine.tomar_decision()
   ├─> Evaluar 6 criterios ponderados:
   │   ├─ Patrón recurrencia (35%)
   │   ├─ Proveedor confiable (20%)
   │   ├─ Monto razonable (15%)
   │   ├─ Fecha esperada (15%)
   │   ├─ Orden compra (10%)
   │   └─ Historial aprobaciones (5%)
   ├─> Aplicar ajuste de historial_pagos
   └─> Score final >= 85% → AUTO-APROBACIÓN

4. Resultado
   ├─> AUTO_APROBADA: estado = aprobada_auto
   ├─> REVISIÓN_MANUAL: estado = en_revision
   └─> Auditoría: registro en automation_audit
```

---

## 📚 Guía de Implementación

### Paso 1: Ejecutar Migration

```bash
# Verificar que existe la tabla historial_pagos
alembic current

# Si no existe, ejecutar migration
alembic upgrade head
```

### Paso 2: Importar Historial Inicial (ONE-TIME)

```bash
# Ajustar ruta del CSV en el script
# Línea 596: ARCHIVO_CSV = r"C:\ruta\al\archivo.csv"

python -m app.scripts.importar_historial_excel
```

**Verificación:**
```sql
-- Verificar que se crearon patrones
SELECT
    tipo_patron,
    COUNT(*) as cantidad,
    SUM(puede_aprobar_auto) as auto_aprobables
FROM historial_pagos
GROUP BY tipo_patron;

-- Output esperado:
-- TIPO_A | 42 | 42
-- TIPO_B | 31 | 26
-- TIPO_C | 12 | 0
```

### Paso 3: Configurar Análisis Periódico

**Opción A: Celery (recomendado para producción)**

```python
# celeryconfig.py
from celery.schedules import crontab

beat_schedule = {
    'analizar-patrones-diario': {
        'task': 'analizar_patrones_periodico',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM
        'args': (12,)  # 12 meses de ventana
    }
}
```

**Opción B: APScheduler (simple, sin Redis)**

```python
# app/main.py
from app.tasks.analisis_patrones_task import configurar_apscheduler

@app.on_event("startup")
def startup_event():
    scheduler = configurar_apscheduler()
    if scheduler:
        scheduler.start()
```

**Opción C: Cron (Linux/Unix)**

```bash
# Agregar a crontab
0 2 * * * cd /path/to/app && python -m app.tasks.analisis_patrones_task
```

### Paso 4: Verificar Integración

```python
# Test manual de integración
from app.db.session import SessionLocal
from app.services.automation.automation_service import AutomationService

db = SessionLocal()
automation = AutomationService()

# Procesar facturas pendientes
resultado = automation.procesar_facturas_pendientes(db, limite_facturas=10)

print(f"Procesadas: {resultado['facturas_procesadas']}")
print(f"Auto-aprobadas: {resultado['aprobadas_automaticamente']}")
print(f"Revisión manual: {resultado['enviadas_revision']}")
```

---

## 🌐 API Endpoints

### POST `/api/v1/historial-pagos/analizar-patrones`

Ejecuta análisis de patrones desde BD.

**Request:**
```json
{
  "ventana_meses": 12,
  "solo_proveedores": [1, 5, 10],
  "forzar_recalculo": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Análisis completado exitosamente",
  "data": {
    "exito": true,
    "estadisticas": {
      "facturas_analizadas": 450,
      "patrones_detectados": 85,
      "patrones_nuevos": 12,
      "patrones_actualizados": 68,
      "patrones_mejorados": 5,
      "patrones_degradados": 2
    }
  }
}
```

---

### GET `/api/v1/historial-pagos/patrones`

Lista patrones con filtros.

**Query params:**
- `proveedor_id`: int (opcional)
- `tipo_patron`: TIPO_A | TIPO_B | TIPO_C (opcional)
- `solo_auto_aprobables`: boolean
- `skip`: int (default: 0)
- `limit`: int (default: 50)

**Response:**
```json
{
  "success": true,
  "data": {
    "patrones": [
      {
        "id": 1,
        "proveedor_id": 5,
        "proveedor_nombre": "KION",
        "concepto_normalizado": "historia clinica - gomedisys",
        "tipo_patron": "TIPO_A",
        "monto_promedio": 70308000.0,
        "coeficiente_variacion": 2.3,
        "puede_aprobar_auto": true,
        "pagos_analizados": 9
      }
    ],
    "total": 85,
    "skip": 0,
    "limit": 50
  }
}
```

---

### GET `/api/v1/historial-pagos/estadisticas`

Estadísticas globales.

**Response:**
```json
{
  "success": true,
  "data": {
    "total": 85,
    "por_tipo": {
      "TIPO_A": 42,
      "TIPO_B": 31,
      "TIPO_C": 12
    },
    "auto_aprobables": 68,
    "porcentaje_automatizable": 80.0,
    "proveedores_unicos": 23
  }
}
```

---

### GET `/api/v1/historial-pagos/patrones/{id}`

Detalle completo de un patrón.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "proveedor": {
      "id": 5,
      "razon_social": "KION",
      "nit": "900123456-7"
    },
    "clasificacion": {
      "tipo": "TIPO_A",
      "descripcion": "Valor fijo"
    },
    "estadisticas": {
      "monto_promedio": 70308000.0,
      "monto_minimo": 68500000.0,
      "monto_maximo": 72100000.0,
      "desviacion_estandar": 1620000.0,
      "coeficiente_variacion": 2.3
    },
    "automatizacion": {
      "puede_aprobar_auto": true,
      "umbral_alerta": 15.0
    }
  }
}
```

---

## ⚙️ Configuración y Mantenimiento

### Variables de Configuración

```python
# app/services/analisis_patrones_service.py
UMBRAL_TIPO_A = 5.0   # CV < 5% = Fijo
UMBRAL_TIPO_B = 30.0  # CV < 30% = Fluctuante
MIN_FACTURAS_PATRON = 3
MIN_MESES_DIFERENTES = 2

# app/services/automation/decision_engine.py
confianza_aprobacion_automatica = 0.85  # 85%
max_monto_aprobacion_automatica = 50000000  # $50M COP
```

### Monitoreo y Métricas

**Métricas clave a monitorear:**

1. **Tasa de automatización:** `auto_aprobadas / total_procesadas`
   - Objetivo: >60%

2. **Precisión de auto-aprobación:** `auto_aprobadas_correctas / auto_aprobadas`
   - Objetivo: >95%

3. **Tiempo de procesamiento:** Promedio por factura
   - Objetivo: <2 segundos

4. **Patrones desactualizados:** `WHERE fecha_analisis < NOW() - INTERVAL '7 days'`
   - Objetivo: <10%

**Query de monitoreo:**
```sql
-- Dashboard de automatización
SELECT
    DATE(fecha_procesamiento_auto) as fecha,
    COUNT(*) as total,
    SUM(CASE WHEN estado = 'aprobada_auto' THEN 1 ELSE 0 END) as auto_aprobadas,
    AVG(confianza_automatica) as confianza_promedio
FROM facturas
WHERE fecha_procesamiento_auto >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(fecha_procesamiento_auto)
ORDER BY fecha DESC;
```

---

## 🔍 Troubleshooting

### Problema: Baja tasa de auto-aprobación

**Síntomas:** Menos del 40% de facturas se auto-aprueban

**Diagnóstico:**
```python
# Verificar patrones disponibles
stats = analizador.obtener_estadisticas_patrones()
print(f"Auto-aprobables: {stats['porcentaje_automatizable']:.1f}%")

# Si <50%, ejecutar análisis con ventana mayor
analizador.analizar_patrones_desde_bd(ventana_meses=18)
```

**Soluciones:**
1. ✅ Aumentar ventana de análisis (12 → 18 meses)
2. ✅ Reducir `confianza_aprobacion_automatica` (0.85 → 0.80)
3. ✅ Verificar que `importar_historial_excel.py` se ejecutó correctamente

---

### Problema: Patrones desactualizados

**Síntomas:** `fecha_analisis` > 7 días

**Diagnóstico:**
```sql
SELECT COUNT(*)
FROM historial_pagos
WHERE fecha_analisis < NOW() - INTERVAL '7 days';
```

**Soluciones:**
1. ✅ Verificar que la tarea programada está activa
2. ✅ Ejecutar análisis manual:
```bash
python -m app.tasks.analisis_patrones_task
```
3. ✅ Forzar recálculo:
```bash
curl -X POST http://localhost:8000/api/v1/historial-pagos/analizar-patrones \
  -H "Content-Type: application/json" \
  -d '{"ventana_meses": 12, "forzar_recalculo": true}'
```

---

### Problema: Errores en importación Excel

**Síntomas:** `errores > 0` en output del script

**Diagnóstico:**
```python
resultado = importador.importar_desde_csv(file_path)
for error in resultado['errores']:
    print(error)
```

**Soluciones comunes:**
1. ✅ Verificar encoding del CSV (debe ser UTF-8)
2. ✅ Validar estructura de columnas (NOMB CTA, Responsable, Ej Ene-25, etc.)
3. ✅ Revisar que los montos sean numéricos
4. ✅ Verificar que existen proveedores en BD

---

## 📊 Métricas de Éxito

### KPIs del Sistema

| Métrica | Baseline | Objetivo | Actual |
|---------|----------|----------|--------|
| Tasa de automatización | 0% | 60% | - |
| Tiempo de aprobación (promedio) | 48h | 2min | - |
| Precisión de auto-aprobación | N/A | 95% | - |
| Facturas procesadas/hora | 50 | 500 | - |
| Reducción de carga manual | 0% | 70% | - |

---

## 🎓 Conceptos Clave

### Coeficiente de Variación (CV%)

El CV mide la variabilidad relativa de un conjunto de datos:

```
CV% = (σ / μ) × 100

Donde:
- σ = desviación estándar
- μ = media

Ejemplo:
Factura KION - Historia Clínica
- Montos: [70M, 71M, 69M, 70.5M, 70M]
- Promedio (μ): 70.1M
- Desv. Std (σ): 0.7M
- CV% = (0.7 / 70.1) × 100 = 1.0% → TIPO_A (fijo)
```

### Ventana de Análisis

Período de tiempo hacia atrás considerado para análisis.

**Recomendaciones:**
- **12 meses:** Balance entre datos suficientes y relevancia
- **6 meses:** Para proveedores nuevos o con cambios recientes
- **18 meses:** Para patrones muy estables (TIPO_A)

### Score de Confianza

Métrica compuesta (0-1) que indica probabilidad de aprobación correcta.

**Componentes:**
```
Score = Σ (criterio_i × peso_i)

Donde:
- Patrón recurrencia: 35%
- Proveedor confiable: 20%
- Monto razonable: 15%
- Fecha esperada: 15%
- Orden compra: 10%
- Historial: 5%

+ Ajuste historial_pagos: ±30%

Score >= 85% → AUTO-APROBACIÓN
```

---

## 📞 Soporte

Para preguntas o issues:

1. **Logs del sistema:** `logs/automation_service.log`
2. **Auditoría:** Tabla `automation_audit`
3. **Métricas:** API endpoint `/api/v1/historial-pagos/estadisticas`

---

**Documento generado automáticamente por el Sistema de Automatización AFE**
**Última actualización:** 2025-10-08
