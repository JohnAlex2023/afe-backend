# 🚀 Quick Start - Sistema de Automatización

Guía rápida de 5 minutos para poner en marcha el sistema de automatización de facturas.

---

## ✅ Pre-requisitos

- ✅ Python 3.9+
- ✅ Base de datos PostgreSQL/MySQL
- ✅ Tabla `historial_pagos` creada (migration)
- ✅ Excel/CSV con historial de facturas 2025

---

## 📋 Paso a Paso (5 minutos)

### 1️⃣ Importar Historial Inicial (ONE-TIME)

```bash
# Editar ruta del archivo CSV
nano app/scripts/importar_historial_excel.py
# Línea 596: ARCHIVO_CSV = r"C:\tu\ruta\al\archivo.csv"

# Ejecutar importación
python -m app.scripts.importar_historial_excel
```

**Output esperado:**
```
✅ IMPORTACIÓN COMPLETADA EXITOSAMENTE
Total patrones detectados: 85
🤖 Patrones auto-aprobables: 68 (80.0%)
```

---

### 2️⃣ Verificar Importación

```bash
# Opción A: SQL directo
psql -d afe_db -c "SELECT tipo_patron, COUNT(*) FROM historial_pagos GROUP BY tipo_patron;"

# Opción B: API
curl http://localhost:8000/api/v1/historial-pagos/estadisticas
```

---

### 3️⃣ Ejecutar Análisis Manual (Primera vez)

```bash
python -m app.tasks.analisis_patrones_task
```

**O usando la API:**
```bash
curl -X POST http://localhost:8000/api/v1/historial-pagos/analizar-patrones \
  -H "Content-Type: application/json" \
  -d '{"ventana_meses": 12, "forzar_recalculo": false}'
```

---

### 4️⃣ Configurar Tarea Programada

**Opción A: APScheduler (Recomendado para desarrollo)**

```python
# app/main.py
from app.tasks.analisis_patrones_task import configurar_apscheduler

@app.on_event("startup")
def startup_event():
    scheduler = configurar_apscheduler()
    if scheduler:
        scheduler.start()
        print("✅ Scheduler iniciado - análisis diario a las 2:00 AM")
```

**Opción B: Cron (Linux)**

```bash
# Editar crontab
crontab -e

# Agregar línea (ejecutar diariamente a las 2 AM)
0 2 * * * cd /path/to/afe-backend && python -m app.tasks.analisis_patrones_task >> /var/log/analisis_patrones.log 2>&1
```

---

### 5️⃣ Probar Automatización

```bash
# Opción A: Procesar facturas pendientes via API
curl -X POST http://localhost:8000/api/v1/automation/procesar-pendientes?limit=10

# Opción B: Script Python
python <<EOF
from app.db.session import SessionLocal
from app.services.automation.automation_service import AutomationService

db = SessionLocal()
automation = AutomationService()

resultado = automation.procesar_facturas_pendientes(db, limite_facturas=10)

print(f"✅ Procesadas: {resultado['facturas_procesadas']}")
print(f"🤖 Auto-aprobadas: {resultado['aprobadas_automaticamente']}")
print(f"👤 Revisión manual: {resultado['enviadas_revision']}")
print(f"📊 Tasa automatización: {resultado['tasa_automatizacion']:.1f}%")

db.close()
EOF
```

---

## 📊 Dashboard Rápido

### Ver Patrones Detectados

```bash
# Top 10 patrones auto-aprobables
curl "http://localhost:8000/api/v1/historial-pagos/patrones?solo_auto_aprobables=true&limit=10"
```

### Ver Estadísticas Globales

```bash
curl http://localhost:8000/api/v1/historial-pagos/estadisticas
```

### Ver Patrones de un Proveedor

```bash
# Reemplazar {proveedor_id} por el ID real
curl http://localhost:8000/api/v1/historial-pagos/proveedor/5/patrones
```

---

## 🔧 Ajustes de Configuración

### Ajustar Umbrales de Auto-aprobación

```python
# app/services/automation/decision_engine.py (línea 61)

self.config = {
    'confianza_aprobacion_automatica': 0.85,  # 85% → ajustar aquí
    'max_monto_aprobacion_automatica': Decimal('50000000'),  # $50M → ajustar aquí
    'max_variacion_monto_porcentaje': 20.0,  # 20% → ajustar aquí
}
```

### Ajustar Clasificación de Patrones

```python
# app/services/analisis_patrones_service.py (línea 56)

UMBRAL_TIPO_A = Decimal('5.0')   # CV < 5% = Fijo → ajustar aquí
UMBRAL_TIPO_B = Decimal('30.0')  # CV < 30% = Fluctuante → ajustar aquí
```

---

## 🐛 Troubleshooting Rápido

### Problema: No se auto-aprueban facturas

```bash
# 1. Verificar que existen patrones
curl http://localhost:8000/api/v1/historial-pagos/estadisticas

# 2. Verificar score de confianza de facturas procesadas
psql -d afe_db -c "SELECT numero_factura, confianza_automatica, motivo_decision FROM facturas WHERE fecha_procesamiento_auto IS NOT NULL ORDER BY fecha_procesamiento_auto DESC LIMIT 10;"

# 3. Si confianza < 85%, revisar criterios
# Ver: SISTEMA_AUTOMATIZACION_PATRONES.md sección "decision_engine"
```

### Problema: Errores en importación

```bash
# Ver logs detallados
python -m app.scripts.importar_historial_excel 2>&1 | tee import.log

# Verificar encoding del CSV
file -i tu_archivo.csv
# Debe decir: charset=utf-8

# Si no es UTF-8, convertir:
iconv -f ISO-8859-1 -t UTF-8 archivo_original.csv > archivo_utf8.csv
```

### Problema: Tarea programada no ejecuta

```bash
# Verificar logs de APScheduler
tail -f logs/apscheduler.log

# Verificar cron (si usas cron)
crontab -l
grep CRON /var/log/syslog

# Ejecutar manualmente para verificar
python -m app.tasks.analisis_patrones_task
```

---

## 📚 Siguiente Paso

Para documentación completa y avanzada:

👉 **[SISTEMA_AUTOMATIZACION_PATRONES.md](SISTEMA_AUTOMATIZACION_PATRONES.md)**

---

## 🎯 Métricas de Éxito

Después de 1 semana, deberías ver:

- ✅ **60-80%** de facturas recurrentes auto-aprobadas
- ✅ **<2 segundos** tiempo de procesamiento por factura
- ✅ **>95%** precisión en auto-aprobaciones
- ✅ **70%** reducción en carga de trabajo manual

---

**¿Problemas? Revisa:** [SISTEMA_AUTOMATIZACION_PATRONES.md - Troubleshooting](SISTEMA_AUTOMATIZACION_PATRONES.md#troubleshooting)
