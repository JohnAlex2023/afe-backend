# Sistema de Automatización Inteligente de Facturas

## 📋 Descripción General

Sistema empresarial de automatización inteligente para procesamiento y aprobación de facturas, diseñado para reducir el trabajo manual en un 80-90% mediante la detección de patrones, análisis de confianza y toma de decisiones automatizada.

## 🏗️ Arquitectura del Sistema

### Pipeline de Automatización (5 Fases)

```
┌─────────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐    ┌───────────┐
│ 1. Detección│ -> │2. Análisis│ -> │3. Decisión│ -> │4. Acción│ -> │5. Auditoría│
└─────────────┘    └──────────┘    └──────────┘    └─────────┘    └───────────┘
```

### Componentes Principales

#### 1. **Motor de Reglas** (`decision_engine.py`)
- Evaluación de criterios múltiples con pesos configurables
- Sistema de puntuación ponderada (0.0 - 1.0)
- Detección de criterios bloqueantes
- Configuración flexible de umbrales

**Criterios Evaluados:**
- ✅ Patrón de recurrencia (35%)
- ✅ Proveedor confiable (20%)
- ✅ Monto razonable (15%)
- ✅ Fecha esperada (15%)
- ✅ Orden de compra válida (10%)
- ✅ Historial de aprobaciones (5%)

#### 2. **Detector de Patrones** (`pattern_detector.py`)
- Análisis de patrones temporales (mensual, quincenal, semanal)
- Análisis de patrones de montos
- Detección de recurrencia con confianza estadística
- Predicción de próxima factura

**Patrones Temporales Detectados:**
- 📅 Semanal (6-9 días)
- 📅 Quincenal (13-17 días)
- 📅 Mensual (26-35 días)
- 📅 Bimestral (60-95 días)
- 📅 Trimestral (85-105 días)

#### 3. **Sistema de Confianza** (Trust Scoring)
- Score de confianza por proveedor (0.00 - 1.00)
- Niveles: Alto (>0.85), Medio (0.50-0.85), Bajo (<0.50), Bloqueado
- Actualización dinámica basada en historial
- Gestión de proveedores bloqueados

**Umbrales de Decisión:**
- 🟢 **Alta Confianza (≥85%)**: Aprobación automática inmediata
- 🟡 **Media Confianza (80-95%)**: Aprobación con alerta
- 🔴 **Baja Confianza (<80%)**: Envío a revisión manual

#### 4. **Servicio de Métricas** (`metrics_service.py`)
- Métricas en tiempo real (día, mes, 24h)
- Cálculo de ROI y ahorro de tiempo
- Dashboard de salud del sistema
- Tendencias y análisis histórico

#### 5. **Machine Learning Service** (`ml_service.py`)
**Fase 1 (Actual):** Heurísticas avanzadas
**Fase 2 (Futuro):** Modelos ML entrenados

**Capacidades:**
- Predicción de aprobación
- Detección de anomalías
- Detección de fraude
- Sistema de feedback para mejora continua

#### 6. **Sistema de Auditoría** (`automation_audit.py`)
- Registro completo de todas las decisiones
- Trazabilidad 100%
- Soporte para override manual
- Feedback para ML

---

## 📊 Modelos de Base de Datos

### `automation_audit`
Registro de auditoría de cada decisión automática.

**Campos principales:**
- `factura_id`: Factura procesada
- `decision`: aprobada_auto | en_revision | rechazada
- `confianza`: Score 0.00-1.00
- `motivo`: Explicación de la decisión
- `criterios_evaluados`: JSON con criterios y pesos
- `override_manual`: Si hubo intervención humana
- `tiempo_procesamiento_ms`: Performance

### `automation_metrics`
Métricas agregadas por período (horario/diario).

**Métricas clave:**
- Tasa de automatización (%)
- Tasa de precisión (%)
- Tiempo promedio de procesamiento
- Montos procesados
- Patrones detectados

### `proveedor_trust`
Trust score y estadísticas por proveedor.

**Datos:**
- `trust_score`: 0.00-1.00
- `nivel_confianza`: alto | medio | bajo | bloqueado
- Tasas de aprobación histórica
- Patrones recurrentes identificados
- Flags de bloqueo

### `configuracion_automatizacion`
Configuración persistente del sistema.

**Parámetros configurables:**
- Umbrales de confianza
- Días de historial
- Variación de monto permitida
- Monto máximo para aprobación
- Flags de activación

---

## 🚀 API Endpoints

### Dashboard y Monitoreo

#### `GET /api/v1/automation/dashboard/metricas`
Métricas en tiempo real del sistema.

**Response:**
```json
{
  "timestamp": "2025-10-08T12:00:00Z",
  "dia_actual": {...},
  "mes_actual": {...},
  "ultimas_24h": {
    "total_procesadas": 45,
    "aprobadas_automaticamente": 38,
    "tasa_automatizacion": 84.44,
    "tasa_precision": 92.11
  },
  "salud_sistema": {
    "estado": "excelente",
    "score": 88.2,
    "alertas": []
  }
}
```

#### `GET /api/v1/automation/dashboard/salud`
Estado de salud del sistema.

**Estados posibles:**
- `excelente`: Tasa auto ≥75%, precisión ≥90%
- `bueno`: Tasa auto ≥60%, precisión ≥80%
- `moderado`: Tasa auto ≥40%, precisión ≥70%
- `necesita_atencion`: Por debajo de umbrales

#### `GET /api/v1/automation/dashboard/alertas`
Alertas activas del sistema.

**Tipos de alertas:**
- Facturas con baja confianza pendientes
- Proveedores bloqueados
- Múltiples overrides manuales
- Salud del sistema degradada

### Control y Gestión

#### `POST /api/v1/automation/control/override`
Override manual de una decisión automática.

**Request:**
```json
{
  "factura_id": 123,
  "nueva_decision": "aprobada",
  "motivo": "Proveedor verificado manualmente",
  "usuario": "juan.perez"
}
```

#### `POST /api/v1/automation/control/feedback`
Feedback sobre decisión para mejorar ML.

**Request:**
```json
{
  "audit_id": 456,
  "resultado": "correcto",
  "comentario": "Decisión acertada"
}
```

#### `POST /api/v1/automation/control/bloquear-proveedor/{id}`
Bloquea un proveedor de aprobaciones automáticas.

#### `POST /api/v1/automation/control/actualizar-trust`
Actualiza manualmente el trust score de un proveedor.

### Procesamiento

#### `POST /api/v1/automation/procesar`
Ejecuta procesamiento automático de facturas pendientes.

**Request:**
```json
{
  "limite_facturas": 20,
  "modo_debug": false,
  "solo_proveedor_id": null,
  "forzar_reprocesamiento": false
}
```

#### `GET /api/v1/automation/estadisticas`
Estadísticas del sistema de automatización.

#### `GET /api/v1/automation/patrones/{proveedor_id}`
Análisis de patrones de un proveedor específico.

### Reportes

#### `GET /api/v1/automation/reportes/resumen-periodo`
Genera resumen ejecutivo de un período.

**Query params:**
- `fecha_inicio`: YYYY-MM-DD
- `fecha_fin`: YYYY-MM-DD

**Response incluye:**
- Rendimiento (tasas, procesadas)
- ROI (tiempo ahorrado, ahorro en COP)
- Financiero (montos procesados)
- Patrones detectados

---

## ⚙️ Configuración

### Parámetros Principales

| Parámetro | Valor Default | Descripción |
|-----------|---------------|-------------|
| `confianza_minima_aprobacion` | 0.85 | Score mínimo para aprobación auto |
| `confianza_minima_revision` | 0.40 | Score mínimo para revisión |
| `dias_historico_patron` | 90 | Días de historial para patrones |
| `variacion_monto_permitida` | 0.20 | Variación de monto permitida (20%) |
| `max_monto_aprobacion_automatica` | 50,000,000 | Monto máximo en COP |
| `max_dias_diferencia_esperada` | 7 | Días de tolerancia en fecha |

### Pesos de Criterios

```python
{
    'peso_patron_recurrencia': 0.35,      # 35%
    'peso_proveedor_confiable': 0.20,     # 20%
    'peso_monto_razonable': 0.15,         # 15%
    'peso_fecha_esperada': 0.15,          # 15%
    'peso_orden_compra': 0.10,            # 10%
    'peso_historial_aprobaciones': 0.05,  # 5%
}
# Total: 100%
```

---

## 📈 Métricas y KPIs

### Métricas de Rendimiento

1. **Tasa de Automatización**
   ```
   (Facturas aprobadas automáticamente / Total procesadas) × 100
   ```

2. **Tasa de Precisión**
   ```
   (Decisiones correctas sin override / Total decisiones) × 100
   ```

3. **ROI - Ahorro de Tiempo**
   ```
   Facturas procesadas × 0.25 horas (15 min manual por factura)
   ```

4. **ROI - Ahorro Económico**
   ```
   Tiempo ahorrado (horas) × Costo hora humana (default: 50,000 COP)
   ```

### Benchmarks Esperados

| Métrica | Objetivo | Excelente |
|---------|----------|-----------|
| Tasa de Automatización | 75% | 85%+ |
| Tasa de Precisión | 85% | 95%+ |
| Tiempo de procesamiento | <500ms | <200ms |
| Override manual | <15% | <5% |

---

## 🔄 Flujo de Procesamiento

### Paso a Paso

1. **Recepción de Factura**
   - Sistema recibe factura nueva (estado: `pendiente`)
   - Se extrae información del XML

2. **Fingerprint y Normalización**
   - Genera hash del concepto normalizado
   - Extrae items principales
   - Identifica orden de compra

3. **Búsqueda de Historial**
   - Busca facturas similares del mismo proveedor
   - Filtra por concepto normalizado
   - Ordena por fecha (más recientes primero)

4. **Análisis de Patrones**
   - Detector de patrones analiza historial
   - Identifica patrón temporal
   - Analiza estabilidad de montos
   - Calcula confianza del patrón

5. **Motor de Decisión**
   - Evalúa todos los criterios
   - Calcula puntuación ponderada
   - Verifica criterios bloqueantes
   - Toma decisión final

6. **Ejecución de Acción**
   - **Si confianza ≥85%**: Aprueba automáticamente
   - **Si confianza 40-85%**: Envía a revisión manual
   - **Si confianza <40%**: Envía a revisión con alerta

7. **Auditoría**
   - Registra decisión en `automation_audit`
   - Actualiza factura con metadata
   - Calcula métricas
   - Envía notificaciones si aplica

---

## 🎯 Ventajas del Sistema

### ✅ Escalabilidad
- Procesa miles de facturas sin intervención humana
- Performance: <500ms por factura
- Procesamiento en paralelo disponible

### ✅ Velocidad
- Aprobación en segundos vs horas/días manual
- Dashboard en tiempo real
- Métricas instantáneas

### ✅ Consistencia
- Criterios uniformes siempre
- Sin variabilidad humana
- Decisiones documentadas

### ✅ Auditoría
- 100% trazabilidad
- Registro de todas las decisiones
- Soporte para compliance

### ✅ ROI
- Reducción 80-90% del trabajo manual
- Ahorro de tiempo cuantificable
- Liberación de recursos para tareas estratégicas

---

## 🔮 Roadmap - Fase 2

### Machine Learning Avanzado

1. **Modelos Entrenados**
   - Random Forest para clasificación
   - XGBoost para predicción de anomalías
   - Redes neuronales para detección de fraude

2. **Aprendizaje Continuo**
   - Reentrenamiento automático mensual
   - Feedback loop integrado
   - A/B testing de modelos

3. **Características Avanzadas**
   - NLP para análisis de conceptos
   - Clustering de proveedores
   - Detección de patrones complejos

4. **Predicción Proactiva**
   - Alertas de facturas esperadas pero no recibidas
   - Predicción de montos futuros
   - Recomendaciones de presupuesto

---

## 🛠️ Instalación y Configuración

### 1. Ejecutar Migración

```bash
# Crear tablas del sistema de automatización
alembic upgrade head
```

### 2. Verificar Configuración

```bash
# GET configuración actual
curl http://localhost:8000/api/v1/automation/config/parametros
```

### 3. Procesar Facturas Pendientes

```bash
# POST procesar facturas
curl -X POST http://localhost:8000/api/v1/automation/procesar \
  -H "Content-Type: application/json" \
  -d '{
    "limite_facturas": 20,
    "modo_debug": false
  }'
```

### 4. Consultar Dashboard

```bash
# GET métricas del dashboard
curl http://localhost:8000/api/v1/automation/dashboard/metricas
```

---

## 📚 Ejemplos de Uso

### Ejemplo 1: Consultar Salud del Sistema

```python
import requests

response = requests.get('http://localhost:8000/api/v1/automation/dashboard/salud')
salud = response.json()

print(f"Estado: {salud['data']['estado']}")
print(f"Score: {salud['data']['score']}")
print(f"Alertas: {len(salud['data']['alertas'])}")
```

### Ejemplo 2: Override Manual

```python
import requests

payload = {
    "factura_id": 123,
    "nueva_decision": "aprobada",
    "motivo": "Verificación manual completada",
    "usuario": "admin"
}

response = requests.post(
    'http://localhost:8000/api/v1/automation/control/override',
    json=payload
)

print(response.json())
```

### Ejemplo 3: Generar Resumen Mensual

```python
import requests

params = {
    "fecha_inicio": "2025-10-01",
    "fecha_fin": "2025-10-31"
}

response = requests.get(
    'http://localhost:8000/api/v1/automation/reportes/resumen-periodo',
    params=params
)

resumen = response.json()
print(f"Facturas procesadas: {resumen['data']['rendimiento']['total_procesadas']}")
print(f"Tasa automatización: {resumen['data']['rendimiento']['tasa_automatizacion']}%")
print(f"Ahorro estimado: ${resumen['data']['roi']['ahorro_estimado_cop']:,.2f} COP")
```

---

## 🔐 Seguridad y Compliance

### Auditoría
- Todas las decisiones automáticas se registran
- Timestamps con zona horaria
- Usuario responsable de overrides
- Versionado de algoritmos

### Trazabilidad
- Factura → Auditoría → Override → Resultado final
- Metadata completa de criterios evaluados
- Configuración usada en cada decisión

### Control de Acceso
- Endpoints de control requieren autenticación
- Roles y permisos por operación
- Logs de cambios de configuración

---

## 📞 Soporte

Para preguntas o problemas:
- Revisar logs en `automation_audit`
- Consultar alertas del sistema
- Verificar configuración de umbrales
- Analizar métricas de rendimiento

---

## 📄 Licencia

Sistema propietario - AFE Backend

---

**Última actualización:** 2025-10-08
**Versión del sistema:** 1.0
**Autor:** Sistema de Automatización Inteligente AFE
