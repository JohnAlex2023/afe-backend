# 📋 PASOS DE IMPLEMENTACIÓN - Sistema de Automatización

**Estado actual detectado:**
- ✅ Base de datos: Conectada
- ✅ Tabla `historial_pagos`: Existe (0 registros)
- ✅ Migraciones: Aplicadas
- 🔄 **Siguiente:** Importar datos del Excel

---

## **PASO 1: Importar Historial Inicial desde Excel** ⏱️ 2-3 minutos

### 1.1 Verificar la ruta del Excel

```bash
# Tu archivo está en:
C:\Users\jhont\PRIVADO_ODO\AVD PPTO TI 2025 - Presentación JZ - OPEX y Menor Cuantia(TI DSZF).csv

# Verificar que existe:
ls -la "C:\Users\jhont\PRIVADO_ODO\AVD PPTO TI 2025 - Presentación JZ - OPEX y Menor Cuantia(TI DSZF).csv"
```

### 1.2 Ejecutar script de importación

```bash
cd c:/Users/jhont/PRIVADO_ODO/afe-backend

# Ejecutar importación (la ruta ya está configurada en el script)
python -m app.scripts.importar_historial_excel
```

**Output esperado:**
```
================================================================================
IMPORTACIÓN DE HISTORIAL DE FACTURAS - BOOTSTRAP INICIAL
================================================================================
Archivo: C:\Users\jhont\PRIVADO_ODO\AVD PPTO TI 2025...
Año fiscal: 2025
Fecha: 2025-10-08 14:30:00

📁 PASO 1: Cargando archivo CSV...
   ✅ 450 filas cargadas

🔍 PASO 2: Extrayendo datos de facturas...
   ✅ 120 líneas de gasto extraídas

📊 PASO 3: Agrupando por proveedor y concepto...
   ✅ 85 patrones únicos detectados

🧮 PASO 4: Calculando estadísticas y clasificando patrones...
   ✅ Estadísticas calculadas para 85 patrones

💾 PASO 5: Guardando en base de datos...
   ✅ Creados: 82
   ✅ Actualizados: 3

📈 PASO 6: Generando resumen...
   Total patrones detectados: 85
   └─ TIPO_A (Fijo, CV<5%): 42
   └─ TIPO_B (Fluctuante, CV<30%): 31
   └─ TIPO_C (Excepcional, CV>30%): 12

   🤖 Patrones auto-aprobables: 68 (80.0%)

   📊 Estadísticas globales:
      - Proveedores nuevos creados: 15
      - Proveedores encontrados: 8
      - Errores: 0

================================================================================
✅ IMPORTACIÓN COMPLETADA EXITOSAMENTE
================================================================================
```

### 1.3 Verificar que se importaron los datos

```bash
# Opción A: Python
python -c "from app.db.session import SessionLocal; from app.models.historial_pagos import HistorialPagos; db = SessionLocal(); print('Patrones importados:', db.query(HistorialPagos).count()); db.close()"

# Opción B: SQL directo
# MySQL:
mysql -u root -p afe_db -e "SELECT tipo_patron, COUNT(*) as cantidad FROM historial_pagos GROUP BY tipo_patron;"

# PostgreSQL:
psql -d afe_db -c "SELECT tipo_patron, COUNT(*) as cantidad FROM historial_pagos GROUP BY tipo_patron;"
```

**Output esperado:**
```
tipo_patron | cantidad
------------+---------
TIPO_A      |      42
TIPO_B      |      31
TIPO_C      |      12
```

---

## **PASO 2: Probar API de Historial** ⏱️ 1 minuto

### 2.1 Iniciar servidor (si no está corriendo)

```bash
cd c:/Users/jhont/PRIVADO_ODO/afe-backend

# Iniciar FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2.2 Probar endpoints

```bash
# 1. Obtener estadísticas globales
curl http://localhost:8000/api/v1/historial-pagos/estadisticas

# Output esperado:
# {
#   "success": true,
#   "data": {
#     "total": 85,
#     "por_tipo": {"TIPO_A": 42, "TIPO_B": 31, "TIPO_C": 12},
#     "auto_aprobables": 68,
#     "porcentaje_automatizable": 80.0
#   }
# }

# 2. Listar primeros 10 patrones auto-aprobables
curl "http://localhost:8000/api/v1/historial-pagos/patrones?solo_auto_aprobables=true&limit=10"

# 3. Ver patrones TIPO_A (más confiables)
curl "http://localhost:8000/api/v1/historial-pagos/patrones?tipo_patron=TIPO_A&limit=5"
```

---

## **PASO 3: Ejecutar Análisis desde BD** ⏱️ 1-2 minutos

Este paso analiza las facturas que ya tienes en la tabla `facturas` (las que extrajo `invoice_extractor`).

### 3.1 Verificar cuántas facturas hay en BD

```bash
python -c "from app.db.session import SessionLocal; from app.models.factura import Factura, EstadoFactura; db = SessionLocal(); total = db.query(Factura).count(); aprobadas = db.query(Factura).filter(Factura.estado.in_([EstadoFactura.aprobada, EstadoFactura.aprobada_auto])).count(); print(f'Total facturas: {total}'); print(f'Aprobadas: {aprobadas}'); db.close()"
```

### 3.2 Ejecutar análisis

```bash
# Opción A: Script Python directo
python -m app.tasks.analisis_patrones_task

# Opción B: Via API
curl -X POST http://localhost:8000/api/v1/historial-pagos/analizar-patrones \
  -H "Content-Type: application/json" \
  -d '{"ventana_meses": 12, "forzar_recalculo": false}'
```

**Output esperado:**
```
================================================================================
INICIANDO ANÁLISIS PROGRAMADO DE PATRONES
Timestamp: 2025-10-08T14:35:00
Ventana: 12 meses
Forzar recálculo: False
================================================================================
✅ ANÁLISIS COMPLETADO EXITOSAMENTE
   Facturas analizadas: 230
   Patrones detectados: 45
   Patrones nuevos: 8
   Patrones actualizados: 37
   Patrones mejorados: 3
   Patrones degradados: 1
   Errores: 0
================================================================================
```

**Nota:** Si tienes pocas facturas en BD (<50), es normal que detecte pocos patrones nuevos. El Excel ya proveyó la mayoría.

---

## **PASO 4: Probar Automatización** ⏱️ 2 minutos

### 4.1 Verificar facturas pendientes

```bash
python -c "from app.db.session import SessionLocal; from app.models.factura import Factura, EstadoFactura; db = SessionLocal(); pendientes = db.query(Factura).filter(Factura.estado == EstadoFactura.pendiente).count(); print(f'Facturas pendientes: {pendientes}'); db.close()"
```

### 4.2 Procesar facturas pendientes

```bash
# Opción A: Via API
curl -X POST "http://localhost:8000/api/v1/automation/procesar-pendientes?limit=10"

# Opción B: Script Python
python <<'EOF'
from app.db.session import SessionLocal
from app.services.automation.automation_service import AutomationService

db = SessionLocal()
automation = AutomationService()

resultado = automation.procesar_facturas_pendientes(db, limite_facturas=10)

print(f"\n{'='*60}")
print(f"RESULTADOS DE AUTOMATIZACIÓN")
print(f"{'='*60}")
print(f"Facturas procesadas: {resultado['facturas_procesadas']}")
print(f"Auto-aprobadas: {resultado['aprobadas_automaticamente']}")
print(f"Revisión manual: {resultado['enviadas_revision']}")
print(f"Errores: {resultado['errores']}")
print(f"{'='*60}\n")

if resultado['facturas_procesadas'] > 0:
    tasa = (resultado['aprobadas_automaticamente'] / resultado['facturas_procesadas']) * 100
    print(f"Tasa de automatización: {tasa:.1f}%")

    # Mostrar detalle de primeras 3 facturas
    print(f"\nDetalle de facturas procesadas:")
    for i, factura in enumerate(resultado['facturas_procesadas_detalle'][:3], 1):
        print(f"\n{i}. Factura {factura['numero_factura']}:")
        print(f"   Estado: {factura['estado']}")
        print(f"   Confianza: {factura['confianza']:.0%}")
        print(f"   Razón: {factura['razon']}")

db.close()
EOF
```

**Output esperado:**
```
============================================================
RESULTADOS DE AUTOMATIZACIÓN
============================================================
Facturas procesadas: 10
Auto-aprobadas: 7
Revisión manual: 3
Errores: 0
============================================================

Tasa de automatización: 70.0%

Detalle de facturas procesadas:

1. Factura KION-900:
   Estado: aprobada_auto
   Confianza: 92%
   Razón: Alta confianza (92.0%) - patrón recurrente confiable

2. Factura DISR93354:
   Estado: en_revision
   Confianza: 65%
   Razón: Confianza moderada (65.0%) - requiere revisión manual

3. Factura E896:
   Estado: aprobada_auto
   Confianza: 88%
   Razón: Alta confianza (88.0%) - patrón recurrente confiable
```

---

## **PASO 5: Configurar Tarea Programada** ⏱️ 3 minutos

### 5.1 Opción A: APScheduler (Recomendado - Simple)

Edita `app/main.py` y agrega:

```python
from app.tasks.analisis_patrones_task import configurar_apscheduler

@app.on_event("startup")
def startup_event():
    """Inicia scheduler para análisis automático."""
    scheduler = configurar_apscheduler()
    if scheduler:
        scheduler.start()
        logger.info("✅ Scheduler iniciado - análisis diario a las 2:00 AM")
```

Reinicia el servidor:
```bash
# Ctrl+C para detener
# Luego:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verifica en los logs:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
✅ Scheduler iniciado - análisis diario a las 2:00 AM
INFO:     Application startup complete.
```

### 5.2 Opción B: Cron (Linux/WSL)

```bash
# Editar crontab
crontab -e

# Agregar línea (ejecutar diariamente a las 2:00 AM)
0 2 * * * cd /c/Users/jhont/PRIVADO_ODO/afe-backend && /c/Users/jhont/PRIVADO_ODO/afe-backend/venv/bin/python -m app.tasks.analisis_patrones_task >> /var/log/analisis_patrones.log 2>&1
```

### 5.3 Opción C: Celery (Producción avanzada)

Si tienes Redis instalado:

```python
# celeryconfig.py
from celery.schedules import crontab

beat_schedule = {
    'analizar-patrones-diario': {
        'task': 'analizar_patrones_periodico',
        'schedule': crontab(hour=2, minute=0),
        'args': (12,)
    }
}
```

---

## **PASO 6: Verificación Final** ⏱️ 2 minutos

### 6.1 Verificar todo el flujo

```bash
# 1. Patrones en BD
echo "=== PATRONES HISTÓRICOS ==="
python -c "from app.db.session import SessionLocal; from app.models.historial_pagos import HistorialPagos, TipoPatron; db = SessionLocal(); print(f'Total: {db.query(HistorialPagos).count()}'); print(f'TIPO_A: {db.query(HistorialPagos).filter(HistorialPagos.tipo_patron==TipoPatron.TIPO_A).count()}'); print(f'Auto-aprobables: {db.query(HistorialPagos).filter(HistorialPagos.puede_aprobar_auto==1).count()}'); db.close()"

# 2. Facturas procesadas
echo -e "\n=== FACTURAS PROCESADAS ==="
python -c "from app.db.session import SessionLocal; from app.models.factura import Factura, EstadoFactura; db = SessionLocal(); print(f'Total facturas: {db.query(Factura).count()}'); print(f'Auto-aprobadas: {db.query(Factura).filter(Factura.estado==EstadoFactura.aprobada_auto).count()}'); print(f'Pendientes: {db.query(Factura).filter(Factura.estado==EstadoFactura.pendiente).count()}'); db.close()"

# 3. API funciona
echo -e "\n=== API ENDPOINTS ==="
curl -s http://localhost:8000/api/v1/historial-pagos/estadisticas | python -m json.tool | head -20
```

### 6.2 Dashboard de éxito

```bash
python <<'EOF'
from app.db.session import SessionLocal
from app.models.historial_pagos import HistorialPagos, TipoPatron
from app.models.factura import Factura, EstadoFactura

db = SessionLocal()

# Patrones
total_patrones = db.query(HistorialPagos).count()
tipo_a = db.query(HistorialPagos).filter(HistorialPagos.tipo_patron==TipoPatron.TIPO_A).count()
auto_aprobables = db.query(HistorialPagos).filter(HistorialPagos.puede_aprobar_auto==1).count()

# Facturas
total_facturas = db.query(Factura).count()
auto_aprobadas = db.query(Factura).filter(Factura.estado==EstadoFactura.aprobada_auto).count()

print("\n" + "="*70)
print("✅ SISTEMA DE AUTOMATIZACIÓN - DASHBOARD")
print("="*70)
print(f"\n📊 PATRONES HISTÓRICOS:")
print(f"   Total patrones: {total_patrones}")
print(f"   TIPO_A (fijos): {tipo_a}")
print(f"   Auto-aprobables: {auto_aprobables} ({auto_aprobables/total_patrones*100 if total_patrones else 0:.1f}%)")

print(f"\n🤖 FACTURAS:")
print(f"   Total facturas: {total_facturas}")
print(f"   Auto-aprobadas: {auto_aprobadas}")
if total_facturas > 0:
    print(f"   Tasa automatización: {auto_aprobadas/total_facturas*100:.1f}%")

print(f"\n✅ Sistema listo para producción!")
print("="*70 + "\n")

db.close()
EOF
```

---

## **🎯 Checklist Final**

- [ ] **Paso 1:** Excel importado → `historial_pagos` poblado
- [ ] **Paso 2:** API funcionando → endpoints responden
- [ ] **Paso 3:** Análisis BD ejecutado → patrones actualizados
- [ ] **Paso 4:** Automatización probada → facturas auto-aprobadas
- [ ] **Paso 5:** Tarea programada configurada
- [ ] **Paso 6:** Verificación exitosa → Dashboard OK

---

## **📚 Próximos Pasos**

1. **Monitorear:** Revisar logs diarios de la tarea programada
2. **Ajustar:** Modificar umbrales si es necesario (ver `decision_engine.py`)
3. **Optimizar:** Analizar métricas y ajustar según resultados

---

## **🆘 ¿Problemas?**

Consulta:
- [`SISTEMA_AUTOMATIZACION_PATRONES.md`](SISTEMA_AUTOMATIZACION_PATRONES.md) - Troubleshooting completo
- [`QUICKSTART_AUTOMATIZACION.md`](QUICKSTART_AUTOMATIZACION.md) - Guía rápida

---

**¡Listo para empezar! Ejecuta el Paso 1 ahora.** 🚀
