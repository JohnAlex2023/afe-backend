# 🚀 Guía de Inicialización Enterprise del Sistema AFE

**Autor:** Senior Backend Developer
**Nivel:** Fortune 500 Enterprise
**Fecha:** 2025

---

## 📋 Resumen Ejecutivo

Este sistema proporciona **inicialización automatizada y orquestada** de toda la plataforma AFE, incluyendo:

✅ Control Presupuestal Enterprise
✅ Workflow de Aprobación Automática
✅ Vinculación Inteligente Factura-Presupuesto
✅ Sistema de Notificaciones
✅ Dashboard Ejecutivo

## 🎯 Estado Actual

### Datos Existentes
- ✅ **213 facturas** de los últimos 3 meses (importadas vía Microsoft Graph)
- ✅ **Tablas de base de datos** creadas y listas
- ❌ **Líneas de presupuesto** NO importadas (tablas vacías)
- ❌ **Asignaciones NIT-Responsable** NO configuradas
- ❌ **Workflow** NO activado

### Lo que Vamos a Hacer
El sistema de inicialización va a:

1. **Importar presupuesto** desde tu Excel a `lineas_presupuesto`
2. **Auto-configurar asignaciones** NIT → Responsable basándose en las 213 facturas existentes
3. **Vincular automáticamente** las 213 facturas con las líneas de presupuesto
4. **Activar workflow** de aprobación automática para facturas futuras

---

## 🚀 Métodos de Inicialización

Tienes **3 opciones** para ejecutar la inicialización:

### Opción 1: API (Swagger/Postman) - ⭐ **Recomendado para Testing**

```bash
POST http://localhost:8000/api/v1/automation/inicializar-sistema?dry_run=true
```

**Ventajas:**
- ✅ Interfaz visual en Swagger
- ✅ Fácil de probar con `dry_run=true`
- ✅ Ver respuesta JSON completa
- ✅ No requiere terminal

### Opción 2: Script CLI - ⭐ **Recomendado para Producción**

```bash
python -m app.scripts.inicializar_sistema_completo \
  --presupuesto "ruta/al/archivo.xlsx" \
  --año 2025 \
  --responsable-id 1 \
  --dry-run  # Quitar para ejecutar real
```

**Ventajas:**
- ✅ Logging detallado en consola
- ✅ Guarda reporte JSON automáticamente
- ✅ Argumentos configurables
- ✅ Ideal para automatización

### Opción 3: Python Directo

```python
from app.db.session import SessionLocal
from app.services.inicializacion_sistema import InicializacionSistemaService

db = SessionLocal()
servicio = InicializacionSistemaService(db)

resultado = servicio.inicializar_sistema_completo(
    archivo_presupuesto="presupuesto_2025.xlsx",
    año_fiscal=2025,
    responsable_default_id=1,
    dry_run=True  # Cambiar a False para ejecutar real
)

print(resultado)
db.close()
```

---

## 📖 Guía Paso a Paso

### PASO 1: DRY RUN (Simulación) ⚠️ IMPORTANTE

**Siempre ejecuta primero en modo DRY RUN** para ver qué va a pasar:

#### Via API:
```
POST http://localhost:8000/api/v1/automation/inicializar-sistema
Query Params:
  - dry_run: true
  - año_fiscal: 2025
  - responsable_default_id: 1
```

#### Via Script:
```bash
python -m app.scripts.inicializar_sistema_completo --dry-run
```

**Qué esperar:**
```json
{
  "exito": true,
  "estado_inicial": {
    "total_facturas": 213,
    "lineas_presupuesto": 0,
    "ejecuciones_presupuestales": 0,
    "asignaciones_nit": 0,
    "workflows_creados": 0
  },
  "estado_final": {
    "total_facturas": 213,
    "lineas_presupuesto": 0,  // Será > 0 si proporcionas archivo
    "ejecuciones_presupuestales": 0,  // Se calculará automáticamente
    "asignaciones_nit": X,  // Basado en tus proveedores únicos
    "workflows_creados": 0
  },
  "duracion_segundos": 5.23,
  "pasos_completados": [...]
}
```

### PASO 2: Preparar Archivo de Presupuesto (Opcional)

Si tienes el Excel de presupuesto:

1. **Ubicación:** Coloca el archivo en una ruta accesible
2. **Formato:** Debe tener las columnas:
   - `ID`: Código de la línea
   - `Nombre cuenta`: Nombre descriptivo
   - `Ene-25`, `Feb-25`, ..., `Dic-25`: Presupuestos mensuales

3. **Ajustar mapeo** (si es necesario):
   - Editar `app/services/excel_to_presupuesto.py`
   - Modificar el dict `mapeo_columnas` según tus nombres de columna

### PASO 3: Ejecutar Inicialización Real

#### Via API (Swagger):

1. Ir a: `http://localhost:8000/docs`
2. Buscar endpoint: `POST /api/v1/automation/inicializar-sistema`
3. Click en "Try it out"
4. Configurar parámetros:
   ```
   archivo_presupuesto: null  (o ruta al Excel)
   año_fiscal: 2025
   responsable_default_id: 1
   ejecutar_vinculacion: true
   ejecutar_workflow: true
   dry_run: false  ⬅️ IMPORTANTE: false para ejecutar real
   ```
5. Click "Execute"
6. Ver respuesta

#### Via Script:

```bash
python -m app.scripts.inicializar_sistema_completo \
  --presupuesto "AVD PPTO TI 2025.xlsx" \
  --año 2025 \
  --responsable-id 1
  # Sin --dry-run = ejecución real
```

**Salida esperada:**
```
================================================================================
🚀 INICIALIZACIÓN ENTERPRISE DEL SISTEMA AFE
================================================================================

📊 PASO 1: Verificando estado actual del sistema...
   📊 Facturas totales: 213
   📊 Líneas de presupuesto: 0
   ✅ Verificación de estado completado

✅ PASO 2: Validando pre-requisitos...
   ✅ Todos los pre-requisitos cumplidos
   ✅ Validación de pre-requisitos completado

📁 PASO 3: Importando presupuesto desde Excel...
   ✅ Líneas creadas: 45
   ✅ Líneas actualizadas: 0
   ✅ Importación de presupuesto completado

🔧 PASO 4: Auto-configurando asignaciones NIT-Responsable...
   ✅ Asignación creada: 900123456 - Microsoft Colombia
   📊 Asignaciones creadas: 25
   ✅ Auto-configuración de asignaciones completado

🔗 PASO 5: Vinculando facturas existentes con presupuesto...
   📊 Total procesadas: 213
   ✅ Vinculadas exitosamente: 187
   ⚠️  Sin vincular: 26
   ✅ Vinculación de facturas completado

⚙️  PASO 6: Activando workflow de aprobación...
   ✅ Workflows creados: 100
   ✅ Activación de workflow completado

================================================================================
✅ INICIALIZACIÓN COMPLETADA EXITOSAMENTE
================================================================================
```

### PASO 4: Verificar Resultados

#### Opción A: Dashboard de Presupuesto
```
GET http://localhost:8000/api/v1/presupuesto/dashboard/2025
```

Verás:
```json
{
  "año_fiscal": 2025,
  "total_lineas": 45,
  "presupuesto_total": 855718668,
  "ejecutado_total": 456789000,
  "saldo_total": 398929668,
  "porcentaje_ejecucion_global": 53.45
}
```

#### Opción B: Dashboard de Workflow
```
GET http://localhost:8000/api/v1/workflow/dashboard
```

Verás:
```json
{
  "facturas_por_estado": {
    "APROBADA_AUTO": 150,
    "PENDIENTE_REVISION": 37,
    "APROBADA_MANUAL": 0
  },
  "total_aprobadas_automaticamente": 150,
  "total_pendientes_revision": 37
}
```

---

## 🔧 Configuración Avanzada

### Ajustar Umbrales de Aprobación Automática

Después de la inicialización, puedes ajustar las asignaciones:

```
PUT http://localhost:8000/api/v1/workflow/asignaciones/{id}
```

```json
{
  "nit": "900123456",
  "responsable_id": 5,
  "area": "TI",
  "permitir_aprobacion_automatica": true,
  "monto_maximo_auto_aprobacion": 20000000,
  "porcentaje_variacion_permitido": 10.0
}
```

### Configurar SMTP para Notificaciones

Editar `app/core/config.py`:

```python
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "notificaciones@tuempresa.com"
SMTP_PASSWORD = "tu_app_password"
FROM_EMAIL = "notificaciones@tuempresa.com"
EMAIL_CONTABILIDAD = "contabilidad@tuempresa.com"
```

---

## 🎬 Workflow Post-Inicialización

### Para Facturas Futuras

Cuando Microsoft Graph guarde una factura nueva:

```python
# En tu código de Microsoft Graph, después de guardar factura:
import requests

requests.post(
    "http://localhost:8000/api/v1/workflow/procesar-factura",
    json={"factura_id": nueva_factura_id}
)
```

El sistema automáticamente:
1. ✅ Identificará el NIT
2. ✅ Asignará al responsable
3. ✅ Comparará con mes anterior
4. ✅ Aprobará automáticamente si es idéntica (similitud ≥ 95%)
5. ✅ O enviará a revisión manual si hay diferencias
6. ✅ Notificará por email

### Tareas Programadas Recomendadas

Crear cron jobs o scheduled tasks:

```bash
# Cada hora: Procesar facturas pendientes
*/60 * * * * curl -X POST http://localhost:8000/api/v1/workflow/procesar-lote

# Cada 15 minutos: Enviar notificaciones pendientes
*/15 * * * * curl -X POST http://localhost:8000/api/v1/workflow/notificaciones/enviar-pendientes

# Diario a las 9am: Enviar recordatorios
0 9 * * * curl -X POST http://localhost:8000/api/v1/workflow/notificaciones/enviar-recordatorios
```

---

## ❓ Troubleshooting

### Error: "Archivo de presupuesto no encontrado"
**Solución:** Proporciona ruta absoluta al archivo

```bash
--presupuesto "C:\Users\tu_usuario\Documents\presupuesto.xlsx"
```

### Error: "Responsable con ID X no existe"
**Solución:** Verifica que el responsable existe en la BD

```sql
SELECT id, nombre, email FROM responsables LIMIT 10;
```

### Muchas facturas "Sin vincular"
**Causas posibles:**
- No hay línea de presupuesto correspondiente
- NIT no coincide
- Nombre de proveedor muy diferente

**Solución:** Revisar facturas manualmente y crear líneas de presupuesto faltantes

### Workflow no se activa para facturas nuevas
**Solución:** Integrar con Microsoft Graph:

```python
# Después de guardar factura en BD
from app.services.workflow_automatico import WorkflowAutomaticoService

workflow_service = WorkflowAutomaticoService(db)
workflow_service.procesar_factura_nueva(factura.id)
```

---

## 📊 Métricas de Éxito

Después de la inicialización, deberías ver:

- ✅ **Líneas de presupuesto:** 40-50 líneas (según tu Excel)
- ✅ **Asignaciones NIT:** 20-30 asignaciones (según proveedores únicos)
- ✅ **Ejecuciones vinculadas:** 150-200 vinculaciones (70-90% de las 213 facturas)
- ✅ **Workflows creados:** 100+ workflows
- ✅ **Aprobaciones automáticas:** 60-80% de facturas aprobadas automáticamente

---

## 🆘 Soporte

Para más información:

- **Documentación de Workflow:** `SISTEMA_WORKFLOW_APROBACION.md`
- **Código de Inicialización:** `app/services/inicializacion_sistema.py`
- **Script CLI:** `app/scripts/inicializar_sistema_completo.py`
- **API Endpoints:** Swagger en `http://localhost:8000/docs`

---

## 🎯 Próximos Pasos

1. ✅ Ejecutar inicialización (este documento)
2. ✅ Revisar dashboard y métricas
3. ✅ Ajustar asignaciones NIT-Responsable según necesidades
4. ✅ Configurar SMTP para notificaciones
5. ✅ Integrar con Microsoft Graph para facturas futuras
6. ✅ Capacitar usuarios en el sistema de aprobación
7. ✅ Configurar tareas programadas
8. ✅ Monitorear y optimizar

---

**¡El sistema está listo para producción!** 🚀
