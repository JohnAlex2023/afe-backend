# 📋 Guía de Uso - Sistema de Workflow de Aprobación Automática

## 🎯 ¿Qué hace este sistema?

El sistema **automatiza la aprobación de facturas** comparándolas con el mes anterior. Si son idénticas, se aprueban automáticamente. Si tienen diferencias, se envían a revisión manual.

---

## 🚀 Flujo Automático

### 1. **Recepción de Factura (Microsoft Graph)**
Cuando llega una factura nueva por correo:

```
📧 Email → Microsoft Graph → BD (tabla facturas) → 🤖 Workflow Automático
```

El workflow se activa **automáticamente** cuando se guarda la factura en la BD.

### 2. **Identificación del Responsable**
El sistema:
1. Extrae el NIT del proveedor
2. Busca en la tabla `asignaciones_nit_responsable`
3. Asigna la factura al responsable configurado

### 3. **Comparación con Mes Anterior**
El sistema busca la factura del mismo proveedor del mes anterior y compara:

| Criterio | Peso | Descripción |
|----------|------|-------------|
| **Proveedor** | 40 puntos | Mismo NIT |
| **Monto** | 40 puntos | Variación ≤ 5% |
| **Concepto** | 20 puntos | Texto similar |

**Total: 100 puntos**

### 4. **Decisión Automática**
- **≥ 95 puntos**: ✅ Aprobación automática
- **< 95 puntos**: ⚠️ Revisión manual requerida

---

## 📡 API Endpoints Principales

### 🔍 **Consultar Mis Facturas Pendientes**

```http
GET /api/v1/workflow/mis-facturas-pendientes?responsable_id=5
```

**Respuesta:**
```json
{
  "total": 15,
  "responsable_id": 5,
  "facturas_pendientes": [
    {
      "workflow_id": 123,
      "factura_id": 456,
      "numero_factura": "E798",
      "proveedor": "KION PROCESOS Y TECNOLOGIA S.A.S",
      "nit": "901261003",
      "monto": 67794987.00,
      "fecha_emision": "2025-01-15",
      "estado": "pendiente_revision",
      "es_identica_mes_anterior": false,
      "porcentaje_similitud": 85.5,
      "dias_pendiente": 2
    }
  ]
}
```

### 📄 **Ver Detalle Completo de una Factura**

```http
GET /api/v1/workflow/factura-detalle/456
```

**Respuesta:**
```json
{
  "factura": {
    "id": 456,
    "numero_factura": "E798",
    "cufe": "abc123...",
    "fecha_emision": "2025-01-15",
    "proveedor": {
      "nit": "901261003",
      "razon_social": "KION PROCESOS Y TECNOLOGIA S.A.S",
      "area": "TI"
    },
    "subtotal": 56975838.00,
    "iva": 10819149.00,
    "total": 67794987.00
  },
  "workflow": {
    "id": 123,
    "estado": "pendiente_revision",
    "tipo_aprobacion": null,
    "responsable_id": 5,
    "area_responsable": "TI",
    "es_identica_mes_anterior": false,
    "porcentaje_similitud": 85.5,
    "diferencias_detectadas": [
      {
        "campo": "monto",
        "actual": 67794987.00,
        "anterior": 70329807.00,
        "variacion_pct": 3.6
      }
    ],
    "factura_mes_anterior": {
      "id": 321,
      "numero": "E721",
      "total": 70329807.00,
      "fecha": "2024-12-15"
    }
  }
}
```

### ✅ **Aprobar Factura Manualmente**

```http
POST /api/v1/workflow/aprobar/123
Content-Type: application/json

{
  "aprobado_por": "John Alex",
  "observaciones": "Aprobado - variación justificada por inflación"
}
```

**Respuesta:**
```json
{
  "exito": true,
  "mensaje": "Factura aprobada exitosamente",
  "workflow_id": 123,
  "estado_nuevo": "aprobada_manual"
}
```

### ❌ **Rechazar Factura**

```http
POST /api/v1/workflow/rechazar/123
Content-Type: application/json

{
  "rechazado_por": "John Alex",
  "motivo": "Monto excesivo sin justificación",
  "detalle": "Requiere cotización adicional"
}
```

### 📊 **Dashboard Ejecutivo**

```http
GET /api/v1/workflow/dashboard?responsable_id=5
```

**Respuesta:**
```json
{
  "resumen": {
    "total_facturas": 213,
    "pendientes_revision": 185,
    "aprobadas_auto": 24,
    "aprobadas_manual": 3,
    "rechazadas": 1
  },
  "metricas": {
    "tasa_aprobacion_auto": 11.3,
    "tiempo_promedio_aprobacion_horas": 4.2,
    "facturas_vencidas": 8
  },
  "por_proveedor": [
    {
      "proveedor": "KION",
      "nit": "901261003",
      "total_facturas": 45,
      "pendientes": 12
    }
  ]
}
```

---

## ⚙️ Configuración de Asignaciones NIT-Responsable

### Ver Asignaciones Actuales

```http
GET /api/v1/workflow/asignaciones
```

### Crear Nueva Asignación

```http
POST /api/v1/workflow/asignaciones
Content-Type: application/json

{
  "nit": "900123456",
  "nombre_proveedor": "NUEVA EMPRESA S.A.S",
  "responsable_id": 5,
  "area": "Compras",
  "permitir_aprobacion_automatica": true,
  "monto_maximo_auto_aprobacion": 10000000,
  "porcentaje_variacion_permitido": 5.0,
  "emails_notificacion": ["responsable@empresa.com"]
}
```

### Actualizar Asignación

```http
PUT /api/v1/workflow/asignaciones/16
Content-Type: application/json

{
  "porcentaje_variacion_permitido": 10.0,
  "monto_maximo_auto_aprobacion": 20000000
}
```

---

## 🔔 Notificaciones

### Enviar Notificaciones Pendientes

```http
POST /api/v1/workflow/notificaciones/enviar-pendientes?limite=100
```

### Enviar Recordatorios (Facturas > 3 días pendientes)

```http
POST /api/v1/workflow/notificaciones/enviar-recordatorios?dias_pendiente=3
```

---

## 📈 Estados del Workflow

| Estado | Descripción |
|--------|-------------|
| `recibida` | Factura recién llegada |
| `en_analisis` | Sistema comparando con mes anterior |
| `aprobada_auto` | Aprobada automáticamente (≥95% similitud) |
| `pendiente_revision` | Requiere revisión manual |
| `requiere_aprobacion_manual` | En espera de aprobación |
| `aprobada_manual` | Aprobada por responsable |
| `rechazada` | Rechazada por responsable |
| `observada` | Tiene observaciones |
| `en_espera` | Esperando información adicional |
| `procesada` | Completada |

---

## 🛠️ Tareas de Mantenimiento

### Procesar Lote de Facturas (Manualmente)

```http
POST /api/v1/workflow/procesar-lote
Content-Type: application/json

{
  "facturas_ids": [1, 2, 3, 4, 5],
  "forzar": false
}
```

### Consultar Estado de un Workflow

```http
GET /api/v1/workflow/consultar/123
```

---

## 📝 Ejemplos de Uso en JavaScript/TypeScript

### Obtener Facturas Pendientes

```typescript
async function obtenerFacturasPendientes(responsableId: number) {
  const response = await fetch(
    `/api/v1/workflow/mis-facturas-pendientes?responsable_id=${responsableId}`
  );
  const data = await response.json();

  console.log(`Tienes ${data.total} facturas pendientes`);
  return data.facturas_pendientes;
}
```

### Aprobar Factura

```typescript
async function aprobarFactura(workflowId: number, usuario: string, obs?: string) {
  const response = await fetch(`/api/v1/workflow/aprobar/${workflowId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      aprobado_por: usuario,
      observaciones: obs
    })
  });

  return await response.json();
}
```

### Ver Detalle de Factura

```typescript
async function verDetalleFactura(facturaId: number) {
  const response = await fetch(`/api/v1/workflow/factura-detalle/${facturaId}`);
  const data = await response.json();

  console.log('Factura:', data.factura.numero_factura);
  console.log('Estado workflow:', data.workflow?.estado);
  console.log('Similitud:', data.workflow?.porcentaje_similitud + '%');

  return data;
}
```

---

## 🔐 Seguridad y Permisos

- Todos los endpoints requieren autenticación
- Los responsables solo pueden ver sus facturas asignadas
- Las aprobaciones quedan registradas con usuario y timestamp
- Auditoría completa en tabla `audit_logs`

---

## 📊 Base de Datos

### Tablas Principales

1. **`workflow_aprobacion_facturas`** - Workflows de aprobación
2. **`asignaciones_nit_responsable`** - Configuración NIT → Responsable
3. **`notificaciones_workflow`** - Historial de notificaciones
4. **`configuracion_correo`** - Config SMTP

### Consultas Útiles (SQL)

```sql
-- Ver facturas pendientes
SELECT
    w.id,
    f.numero_factura,
    p.razon_social,
    w.estado,
    w.porcentaje_similitud
FROM workflow_aprobacion_facturas w
JOIN facturas f ON w.factura_id = f.id
JOIN proveedores p ON f.proveedor_id = p.id
WHERE w.estado IN ('pendiente_revision', 'requiere_aprobacion_manual')
ORDER BY w.creado_en DESC;

-- Ver tasa de aprobación automática
SELECT
    COUNT(*) FILTER (WHERE tipo_aprobacion = 'automatica') * 100.0 / COUNT(*) as tasa_auto
FROM workflow_aprobacion_facturas;
```

---

## ❓ Preguntas Frecuentes

### ¿Qué pasa si un NIT no tiene responsable asignado?
El workflow se crea en estado `pendiente_revision` y queda sin asignar hasta que se configure la asignación.

### ¿Puedo cambiar el porcentaje de similitud requerido?
Sí, editando la asignación del NIT en `/api/v1/workflow/asignaciones/{id}`.

### ¿Las facturas automáticas requieren revisión?
No, se aprueban directamente y quedan registradas en estado `aprobada_auto`.

### ¿Cómo sé qué facturas difieren del mes anterior?
El campo `diferencias_detectadas` en el workflow muestra exactamente qué cambió.

---

## 🎨 Integración con Frontend

### Dashboard Recomendado

```
┌─────────────────────────────────────────┐
│  📊 Dashboard de Aprobaciones           │
├─────────────────────────────────────────┤
│                                         │
│  ⚡ Pendientes: 15                      │
│  ✅ Aprobadas Hoy: 8                    │
│  ❌ Rechazadas: 1                       │
│                                         │
│  📋 FACTURAS PENDIENTES                 │
│  ┌─────────────────────────────────┐   │
│  │ KION - E798  $67,794,987        │   │
│  │ 🟡 85% similar - Monto +3.6%    │   │
│  │ [Ver Detalle] [Aprobar] [Rechazar] │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

---

## 📞 Soporte

Para dudas o problemas:
1. Revisar logs del sistema
2. Consultar tabla `audit_logs`
3. Verificar configuración en `.env`

**Sistema creado por:** Senior Backend Developer
**Nivel:** Fortune 500 Enterprise
**Fecha:** 2025-10-05
