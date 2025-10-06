# Sistema de Workflow de Aprobación Automática de Facturas

## Descripción General

Sistema empresarial de automatización inteligente para la gestión y aprobación de facturas. Integrado con Microsoft Graph para recepción automática de correos.

## 🎯 Objetivos

1. **Recepción Automática**: Las facturas llegan vía correo y son procesadas por Microsoft Graph
2. **Identificación Inteligente**: Extrae el NIT del proveedor y asigna al responsable
3. **Aprobación Automática**: Compara con el mes anterior y aprueba automáticamente si es idéntica
4. **Revisión Manual**: Envía a revisión humana cuando hay diferencias
5. **Notificaciones**: Alerta a responsables y contabilidad en cada etapa
6. **Trazabilidad Completa**: Registro detallado de todas las acciones

## 📊 Base de Datos

### Tablas Creadas

#### 1. `workflow_aprobacion_facturas`
Workflow principal de cada factura.

**Campos clave:**
- `factura_id`: Referencia a la factura
- `estado`: Estado actual (RECIBIDA, EN_ANALISIS, APROBADA_AUTO, PENDIENTE_REVISION, etc.)
- `nit_proveedor`: NIT identificado automáticamente
- `responsable_id`: Responsable asignado
- `es_identica_mes_anterior`: ¿Es igual a la del mes anterior?
- `porcentaje_similitud`: % de similitud (0-100)
- `diferencias_detectadas`: JSON con diferencias encontradas
- `tipo_aprobacion`: AUTOMATICA | MANUAL | MASIVA | FORZADA
- `tiempo_en_analisis`, `tiempo_en_revision`: Métricas de tiempo

#### 2. `asignacion_nit_responsable`
Configuración: NIT → Responsable

**Campos clave:**
- `nit`: NIT del proveedor
- `responsable_id`: Responsable asignado
- `area`: Área responsable (TI, Operaciones, etc.)
- `permitir_aprobacion_automatica`: ¿Permitir auto-aprobación?
- `requiere_revision_siempre`: ¿Siempre requiere revisión manual?
- `monto_maximo_auto_aprobacion`: Monto máximo para auto-aprobar
- `porcentaje_variacion_permitido`: % de variación permitida (default: 5%)

#### 3. `notificaciones_workflow`
Registro de notificaciones enviadas.

#### 4. `configuracion_correo`
Configuración de cuentas de correo (para futuro).

## 🔄 Flujo de Trabajo

### Flujo Completo

```
1. Factura llega por correo
   ↓
2. Microsoft Graph la procesa y guarda en tabla `facturas`
   ↓
3. Sistema detecta nueva factura
   ↓
4. POST /api/v1/workflow/procesar-factura
   ↓
5. Extrae NIT del proveedor
   ↓
6. Busca asignación en `asignacion_nit_responsable`
   ↓
7. Crea registro en `workflow_aprobacion_facturas`
   ↓
8. Busca factura del mes anterior del mismo proveedor
   ↓
9. Compara facturas (proveedor, monto, concepto)
   ↓
10. ¿Es idéntica? (similitud >= 95%)
    ├─ SÍ → Aprobación Automática
    │   ├─ Notifica a responsable y contabilidad
    │   └─ Estado: APROBADA_AUTO
    │
    └─ NO → Revisión Manual
        ├─ Notifica al responsable con diferencias
        └─ Estado: PENDIENTE_REVISION
            ↓
        Responsable revisa
            ↓
        POST /api/v1/workflow/aprobar/{id}
        o
        POST /api/v1/workflow/rechazar/{id}
```

### Estados del Workflow

1. **RECIBIDA**: Factura recibida, workflow creado
2. **EN_ANALISIS**: Analizando similitud con mes anterior
3. **APROBADA_AUTO**: Aprobada automáticamente (idéntica)
4. **PENDIENTE_REVISION**: Requiere revisión manual
5. **EN_REVISION**: Responsable está revisando
6. **APROBADA_MANUAL**: Aprobada manualmente
7. **RECHAZADA**: Rechazada
8. **OBSERVADA**: Tiene observaciones
9. **ENVIADA_CONTABILIDAD**: Enviada a contabilidad
10. **PROCESADA**: Procesada completamente

## 🚀 Endpoints API

### Workflow Principal

#### `POST /api/v1/workflow/procesar-factura`
Procesa una factura nueva.

**Request:**
```json
{
  "factura_id": 123
}
```

**Response:**
```json
{
  "exito": true,
  "workflow_id": 1,
  "factura_id": 123,
  "nit": "900123456",
  "responsable_id": 5,
  "area": "TI",
  "aprobacion_automatica": true,
  "porcentaje_similitud": 100,
  "mensaje": "Factura aprobada automáticamente"
}
```

#### `POST /api/v1/workflow/procesar-lote`
Procesa todas las facturas pendientes en lote.

**Query Params:**
- `limite`: Máximo de facturas a procesar (default: 50)

#### `POST /api/v1/workflow/aprobar/{workflow_id}`
Aprueba manualmente una factura.

**Request:**
```json
{
  "aprobado_por": "carlos@afe.com",
  "observaciones": "Factura correcta, incremento por actualización de tarifas"
}
```

#### `POST /api/v1/workflow/rechazar/{workflow_id}`
Rechaza una factura.

**Request:**
```json
{
  "rechazado_por": "carlos@afe.com",
  "motivo": "MONTO_INCORRECTO",
  "detalle": "El monto no corresponde al servicio prestado"
}
```

#### `GET /api/v1/workflow/consultar/{workflow_id}`
Consulta el estado de un workflow.

#### `GET /api/v1/workflow/listar`
Lista workflows con filtros.

**Query Params:**
- `estado`: Filtrar por estado
- `responsable_id`: Filtrar por responsable
- `nit_proveedor`: Filtrar por NIT
- `skip`, `limit`: Paginación

### Dashboard

#### `GET /api/v1/workflow/dashboard`
Dashboard de métricas.

**Query Params:**
- `responsable_id`: Filtrar por responsable (opcional)

**Response:**
```json
{
  "facturas_por_estado": {
    "RECIBIDA": 5,
    "EN_ANALISIS": 2,
    "APROBADA_AUTO": 150,
    "PENDIENTE_REVISION": 8,
    "APROBADA_MANUAL": 45,
    "RECHAZADA": 3
  },
  "total_aprobadas_automaticamente": 150,
  "total_aprobadas_manualmente": 45,
  "total_rechazadas": 3,
  "total_pendientes_revision": 8,
  "pendientes_hace_mas_3_dias": 2,
  "tiempo_promedio_aprobacion_segundos": 3600,
  "tiempo_promedio_aprobacion_horas": 1.0
}
```

### Asignaciones NIT-Responsable

#### `POST /api/v1/workflow/asignaciones`
Crea una asignación NIT → Responsable.

**Request:**
```json
{
  "nit": "900123456",
  "nombre_proveedor": "Microsoft Colombia",
  "responsable_id": 5,
  "area": "TI",
  "permitir_aprobacion_automatica": true,
  "requiere_revision_siempre": false,
  "monto_maximo_auto_aprobacion": 10000000,
  "porcentaje_variacion_permitido": 5.0,
  "emails_notificacion": ["ti@afe.com", "jefe-ti@afe.com"]
}
```

#### `GET /api/v1/workflow/asignaciones`
Lista todas las asignaciones.

#### `PUT /api/v1/workflow/asignaciones/{id}`
Actualiza una asignación.

### Notificaciones

#### `POST /api/v1/workflow/notificaciones/enviar-pendientes`
Envía notificaciones pendientes en cola.

#### `POST /api/v1/workflow/notificaciones/enviar-recordatorios`
Envía recordatorios para facturas pendientes hace más de X días.

**Query Params:**
- `dias_pendiente`: Días pendiente (default: 3)

## 🔧 Configuración Inicial

### 1. Crear Asignaciones NIT-Responsable

```bash
POST /api/v1/workflow/asignaciones
```

Para cada proveedor, crear una asignación indicando:
- NIT del proveedor
- Responsable que debe aprobar
- Área
- Configuración de aprobación automática

### 2. Configurar Emails (opcional)

En `app/core/config.py` agregar:

```python
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "notificaciones@afe.com"
SMTP_PASSWORD = "app_password"
FROM_EMAIL = "notificaciones@afe.com"
EMAIL_CONTABILIDAD = "contabilidad@afe.com"
```

## 📈 Uso del Sistema

### Caso 1: Factura Recurrente (Aprobación Automática)

```python
# 1. Llega factura de Microsoft por $5,000,000 (igual que el mes pasado)
# 2. Sistema la procesa automáticamente
POST /api/v1/workflow/procesar-factura
{
  "factura_id": 234
}

# Respuesta:
{
  "exito": true,
  "aprobacion_automatica": true,
  "porcentaje_similitud": 100,
  "mensaje": "Factura aprobada automáticamente"
}

# 3. Se envía notificación al responsable y contabilidad
# 4. No requiere acción manual
```

### Caso 2: Factura con Diferencias (Revisión Manual)

```python
# 1. Llega factura de Microsoft por $7,000,000 (mes pasado: $5,000,000)
# 2. Sistema detecta diferencia del 40%
POST /api/v1/workflow/procesar-factura
{
  "factura_id": 235
}

# Respuesta:
{
  "exito": true,
  "requiere_revision": true,
  "porcentaje_similitud": 60,
  "diferencias": [
    {
      "campo": "monto",
      "actual": 7000000,
      "anterior": 5000000,
      "variacion_pct": 40.0
    }
  ],
  "mensaje": "Factura enviada a revisión manual"
}

# 3. Responsable recibe notificación
# 4. Revisa y aprueba:
POST /api/v1/workflow/aprobar/1
{
  "aprobado_por": "carlos@afe.com",
  "observaciones": "Incremento por licencias adicionales"
}
```

### Caso 3: Procesar Lote de Facturas

```python
# Procesar todas las facturas nuevas
POST /api/v1/workflow/procesar-lote?limite=100

# Respuesta:
{
  "total_procesadas": 45,
  "exitosas": 43,
  "errores": [],
  "workflows_creados": [...]
}
```

## 📊 Criterios de Comparación

El sistema compara 3 aspectos:

### 1. Proveedor (40 puntos)
- ✅ Coincidencia exacta: 40 puntos
- ❌ Diferente: 0 puntos

### 2. Monto (40 puntos)
- ✅ Variación ≤ umbral configurado (default 5%): 40 puntos
- ⚠️ Variación entre 5-25%: Proporcional
- ❌ Variación > 25%: 0 puntos

### 3. Concepto (20 puntos)
- ✅ Similitud ≥ 70% de palabras: 20 puntos
- ❌ Similitud < 70%: 0 puntos

**Aprobación Automática:** Score ≥ 95 puntos

## 🔔 Tipos de Notificaciones

1. **FACTURA_RECIBIDA**: Cuando llega una factura nueva
2. **PENDIENTE_REVISION**: Cuando requiere revisión manual
3. **FACTURA_APROBADA**: Cuando se aprueba (auto o manual)
4. **FACTURA_RECHAZADA**: Cuando se rechaza
5. **RECORDATORIO**: Recordatorio de facturas pendientes
6. **ALERTA**: Alertas especiales

## 🎯 Métricas y KPIs

- **Tasa de aprobación automática**: % de facturas aprobadas sin intervención
- **Tiempo promedio de aprobación**: Desde recepción hasta aprobación final
- **Facturas pendientes**: Cantidad en revisión
- **Facturas antiguas**: Pendientes hace más de 3 días
- **Tasa de rechazo**: % de facturas rechazadas

## 🔐 Seguridad

- Control de acceso por responsable
- Registro completo de auditoría (quién, cuándo, qué)
- Trazabilidad de todas las acciones
- Versionamiento de cambios

## 📝 Próximos Pasos Recomendados

1. ✅ **Configurar asignaciones NIT-Responsable**
   - Crear registros para todos los proveedores recurrentes

2. ✅ **Configurar servidor SMTP**
   - Para envío de notificaciones por email

3. ✅ **Crear tarea programada**
   - Ejecutar `POST /api/v1/workflow/procesar-lote` cada hora
   - Ejecutar `POST /api/v1/workflow/notificaciones/enviar-pendientes` cada 15 minutos
   - Ejecutar `POST /api/v1/workflow/notificaciones/enviar-recordatorios` diariamente

4. ✅ **Integrar con Microsoft Graph**
   - Llamar a `POST /api/v1/workflow/procesar-factura` cuando se guarde una nueva factura

5. ✅ **Capacitar usuarios**
   - Dashboard de seguimiento
   - Proceso de aprobación/rechazo manual

## 🌟 Ventajas del Sistema

- ✅ **Automatización Inteligente**: 80-90% de facturas aprobadas automáticamente
- ✅ **Ahorro de Tiempo**: Reduce tiempo de aprobación de horas a minutos
- ✅ **Trazabilidad Completa**: Registro detallado de todas las acciones
- ✅ **Notificaciones Proactivas**: Alerta a responsables automáticamente
- ✅ **Dashboard Ejecutivo**: Visibilidad total del proceso
- ✅ **Configurable**: Umbrales y reglas personalizables por proveedor
- ✅ **Escalable**: Procesa miles de facturas por mes

## 🆘 Soporte

Para más información, consultar:
- Código fuente: `app/services/workflow_automatico.py`
- Modelos: `app/models/workflow_aprobacion.py`
- API: `app/api/v1/routers/workflow.py`
