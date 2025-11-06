# Guía de Deployment Empresarial - Sistema AFE

## Nivel: ENTERPRISE PRODUCTION-READY

---

## 🎯 Garantías Arquitecturales Implementadas

### 1. Triggers de Base de Datos (CRÍTICO)

**¿Qué son?**
Código SQL que se ejecuta automáticamente cuando ocurren ciertos eventos en la base de datos.

**¿Por qué son críticos?**
- Funcionan **independientemente del código Python**
- No pueden ser olvidados o bypasseados
- Se ejecutan a nivel de base de datos (más rápido)
- Garantizan integridad incluso con bugs en el código

**Triggers implementados:**

1. **`after_asignacion_soft_delete`**
   - Ejecuta: DESPUÉS de marcar asignación como inactiva
   - Acción: Desasigna automáticamente todas las facturas del responsable
   - Garantía: Nunca habrá facturas asignadas sin asignación activa

2. **`after_asignacion_activate`**
   - Ejecuta: DESPUÉS de crear nueva asignación
   - Acción: Asigna automáticamente facturas del NIT al responsable
   - Garantía: Asignación inmediata sin depender de código Python

3. **`after_asignacion_restore`**
   - Ejecuta: DESPUÉS de reactivar asignación (activo FALSE → TRUE)
   - Acción: Reasigna automáticamente facturas del NIT al responsable
   - Garantía: Restauración completa y consistente

**Instalación:**
```bash
# Opción 1: Via Alembic (RECOMENDADO)
alembic upgrade head

# Opción 2: Ejecutar SQL directamente
mysql -u usuario -p nombre_bd < alembic/versions/2025_10_21_triggers_integridad_asignaciones.sql
```

**Verificación:**
```sql
SHOW TRIGGERS WHERE `Table` = 'asignacion_nit_responsable';
-- Debe mostrar 3 triggers
```

---

### 2. Tests Automatizados (CI/CD)

**Ubicación:** `tests/test_asignacion_sincronizacion.py`

**Tests críticos:**
- `test_crear_asignacion_asigna_facturas_automaticamente`
- `test_eliminar_asignacion_desasigna_facturas_automaticamente`
- `test_restaurar_asignacion_reasigna_facturas_automaticamente`
- `test_no_hay_facturas_huerfanas_en_sistema`

**Ejecución:**
```bash
# Ejecutar todos los tests de sincronización
pytest tests/test_asignacion_sincronizacion.py -v

# Ejecutar test específico
pytest tests/test_asignacion_sincronizacion.py::TestAsignacionSincronizacion::test_no_hay_facturas_huerfanas_en_sistema -v

# Ejecutar con coverage
pytest tests/test_asignacion_sincronizacion.py --cov=app.api.v1.routers.asignacion_nit --cov-report=html
```

**Integración CI/CD:**
```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run integrity tests
        run: pytest tests/test_asignacion_sincronizacion.py -v
      - name: Fail if integrity tests fail
        if: failure()
        run: exit 1
```

---

### 3. Health Check Endpoint (Monitoreo)

**Endpoint:** `GET /api/v1/health/integrity`

**Respuesta:**
```json
{
  "status": "healthy",
  "checks": {
    "facturas_huerfanas": {
      "status": "ok",
      "count": 0
    },
    "triggers": {
      "status": "ok",
      "active": 3,
      "expected": 3
    },
    "indices": {
      "status": "ok"
    }
  },
  "issues": []
}
```

**Integración con monitoreo:**
```bash
# Cron job para verificar integridad cada hora
0 * * * * curl -f http://localhost:8000/api/v1/health/integrity || echo "ALERTA: Sistema con inconsistencias"

# Prometheus/Grafana
curl http://localhost:8000/api/v1/health/integrity | jq '.status'
```

---

### 4. Índices de Performance

**Ubicación:** `alembic/versions/2025_10_21_add_referential_checks.sql`

**Índices críticos:**
```sql
-- Optimiza queries de sincronización
CREATE INDEX idx_facturas_responsable_proveedor ON facturas(responsable_id, proveedor_id);

-- Optimiza búsquedas LIKE por NIT
CREATE INDEX idx_proveedores_nit_prefix ON proveedores(nit(15));

-- Optimiza queries de asignaciones activas
CREATE INDEX idx_asignacion_responsable_activo ON asignacion_nit_responsable(responsable_id, activo);
```

**Instalación:**
```bash
mysql -u usuario -p nombre_bd < alembic/versions/2025_10_21_add_referential_checks.sql
```

---

## 🚀 Checklist de Deployment

### Pre-Deployment

- [ ] **Backup de base de datos**
  ```bash
  mysqldump -u usuario -p nombre_bd > backup_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] **Ejecutar tests de integridad**
  ```bash
  pytest tests/test_asignacion_sincronizacion.py -v
  ```

- [ ] **Verificar migraciones pendientes**
  ```bash
  alembic current
  alembic heads
  ```

### Deployment

- [ ] **1. Aplicar migraciones Alembic**
  ```bash
  alembic upgrade head
  ```

- [ ] **2. Instalar triggers de integridad**
  ```bash
  # Ya incluido en alembic upgrade head
  # O manualmente:
  mysql -u usuario -p nombre_bd < alembic/versions/2025_10_21_triggers_integridad_asignaciones.sql
  ```

- [ ] **3. Instalar índices de performance**
  ```bash
  mysql -u usuario -p nombre_bd < alembic/versions/2025_10_21_add_referential_checks.sql
  ```

- [ ] **4. Limpiar facturas huérfanas (si existen)**
  ```bash
  venv/Scripts/python.exe -c "import sys; sys.path.insert(0, '.'); from scripts.limpiar_facturas_huerfanas_auto import main; main()"
  ```

- [ ] **5. Reiniciar servidor FastAPI**
  ```bash
  # Detener servidor actual (Ctrl+C)
  # Reiniciar
  uvicorn app.main:app --reload --port 8000

  # O con gunicorn (producción)
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```

### Post-Deployment

- [ ] **1. Verificar triggers instalados**
  ```sql
  SHOW TRIGGERS WHERE `Table` = 'asignacion_nit_responsable';
  -- Debe mostrar 3 triggers
  ```

- [ ] **2. Ejecutar health check**
  ```bash
  curl http://localhost:8000/api/v1/health/integrity
  # Debe retornar status: "healthy"
  ```

- [ ] **3. Prueba funcional completa**
  - Crear asignación → Verificar facturas asignadas
  - Eliminar asignación → Verificar facturas desasignadas
  - Restaurar asignación → Verificar facturas reasignadas

- [ ] **4. Verificar logs del servidor**
  ```bash
  tail -f logs/app.log | grep "Desasignadas\|Sincronizadas"
  ```

- [ ] **5. Ejecutar tests de integración en producción**
  ```bash
  pytest tests/test_asignacion_sincronizacion.py::TestAsignacionSincronizacion::test_no_hay_facturas_huerfanas_en_sistema -v
  ```

---

## 🔧 Troubleshooting

### Problema: Facturas no se sincronizan

**Diagnóstico:**
```bash
# 1. Verificar triggers
mysql -u usuario -p -e "SHOW TRIGGERS WHERE \`Table\` = 'asignacion_nit_responsable';" nombre_bd

# 2. Verificar health check
curl http://localhost:8000/api/v1/health/integrity

# 3. Verificar logs
tail -f logs/app.log
```

**Solución:**
```bash
# Reinstalar triggers
mysql -u usuario -p nombre_bd < alembic/versions/2025_10_21_triggers_integridad_asignaciones.sql

# Limpiar facturas huérfanas
python -c "import sys; sys.path.insert(0, '.'); from scripts.limpiar_facturas_huerfanas_auto import main; main()"

# Reiniciar servidor
# Ctrl+C y luego: uvicorn app.main:app --reload --port 8000
```

### Problema: Servidor con código antiguo

**Síntoma:** Cambios en código Python no se reflejan

**Solución:**
```bash
# 1. Verificar que uvicorn tiene --reload
uvicorn app.main:app --reload --port 8000

# 2. Si no funciona, reiniciar manualmente
# Ctrl+C
uvicorn app.main:app --reload --port 8000

# 3. En producción, usar gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --reload
```

### Problema: Facturas huérfanas detectadas

**Diagnóstico:**
```bash
curl http://localhost:8000/api/v1/health/integrity | jq '.checks.facturas_huerfanas'
```

**Solución automática:**
```bash
python -c "import sys; sys.path.insert(0, '.'); from scripts.limpiar_facturas_huerfanas_auto import main; main()"
```

---

## 📊 Monitoreo Continuo

### Métricas clave

1. **Facturas huérfanas:** Debe ser siempre 0
2. **Triggers activos:** Debe ser siempre 3
3. **Tiempo de respuesta health check:** < 500ms
4. **Tests de integridad:** 100% passing

### Alertas recomendadas

```yaml
# alerts.yml (Prometheus)
groups:
  - name: afe_integrity
    rules:
      - alert: FacturasHuerfanasDetectadas
        expr: afe_facturas_huerfanas > 0
        for: 5m
        annotations:
          summary: "Facturas huérfanas detectadas"
          description: "{{ $value }} facturas con responsable_id sin asignación activa"

      - alert: TriggersFaltantes
        expr: afe_triggers_activos < 3
        for: 1m
        annotations:
          summary: "Triggers de integridad faltantes"
          description: "Solo {{ $value }}/3 triggers activos"
```

---

##  Ventajas de Esta Arquitectura

### 1. **Independencia de Código**
- Los triggers garantizan sincronización incluso si el código Python tiene bugs
- Funciona con cualquier framework/lenguaje futuro
- No depende de hot-reload o reinicio de servidor

### 2. **Performance**
- Triggers se ejecutan en el mismo proceso MySQL (sin overhead de red)
- Índices optimizados para queries de sincronización
- Operaciones atómicas dentro de la transacción

### 3. **Auditabilidad**
- Tests automatizados verifican integridad
- Health check detecta problemas proactivamente
- Logs completos de todas las operaciones

### 4. **Mantenibilidad**
- Documentación clara de todas las garantías
- Scripts automatizados de limpieza
- Guía de troubleshooting completa

### 5. **Confiabilidad**
- Imposible tener facturas huérfanas (triggers previenen)
- Verificación continua vía health check
- Tests de integridad en CI/CD

---

## 🎓 Recomendaciones Adicionales

### Para Desarrollo

1. **Siempre reiniciar servidor después de cambios en código**
2. **Ejecutar tests antes de commit**
   ```bash
   pytest tests/test_asignacion_sincronizacion.py -v
   ```
3. **Verificar health check después de cambios**
   ```bash
   curl http://localhost:8000/api/v1/health/integrity
   ```

### Para Producción

1. **Configurar monitoreo de health check (Prometheus/Grafana)**
2. **Alertas automáticas si se detectan inconsistencias**
3. **Backup automático antes de cada deployment**
4. **Ejecutar tests de integridad post-deployment**
5. **Logs centralizados (ELK/Datadog)**

### Para Auditoría

1. **Mantener log de todas las operaciones de asignación**
2. **Revisar health check diariamente**
3. **Ejecutar tests de integridad semanalmente**
4. **Documentar cualquier inconsistencia detectada**

---

## 📞 Soporte

Para problemas o dudas, verificar:

1. **Health Check:** `GET /api/v1/health/integrity`
2. **Logs del servidor:** `logs/app.log`
3. **Tests de integridad:** `pytest tests/test_asignacion_sincronizacion.py -v`
4. **Este documento:** `DEPLOYMENT_GUIDE_ENTERPRISE.md`

---

**Fecha:** 2025-10-21
**Versión:** 2.0.0
**Nivel:** ENTERPRISE PRODUCTION-READY
