# DATA SYNCHRONIZATION RULES

**🔐 CRITICAL DOCUMENT: Reglas exhaustivas de sincronización de datos**

---

## I. PRINCIPIOS FUNDAMENTALES

### 1.1 Single Source of Truth (SSOT)
Para **cada dato**, existe UNA ÚNICA FUENTE:

```
DATO → FUENTE ÚNICA → LECTURAS (múltiples, siempre consistentes)

✓ accion_por → facturas.accion_por
✓ responsable → facturas.responsable_id
✓ estado → facturas.estado
✓ aprobada_por (audit) → workflow_aprobacion_facturas.aprobada_por
```

**Regla:** Si un dato viene de múltiples fuentes, es un ERROR.

### 1.2 Sincronización Automática, No Manual
Todos los cambios se sincronizan **automáticamente** en una transacción:

```
NUNCA hacer: UPDATE facturas SET accion_por = '...'  (manual)
SIEMPRE hacer: workflow.aprobada_por = '...' → auto-sync a factura.accion_por
```

### 1.3 Atomic Transactions
Cambios relacionados DEBEN ser atómicos:

```python
# CORRECTO:
session.begin()
try:
    workflow.aprobada_por = "Juan"
    factura.accion_por = "Juan"
    factura.estado = "aprobada"
    session.commit()  # TODO O NADA
except:
    session.rollback()

# INCORRECTO:
workflow.aprobada_por = "Juan"
session.commit()
factura.accion_por = "Juan"
session.commit()  # ¿Qué pasa si esto falla?
```

---

## II. MAPEO DE DATOS Y SUS FUENTES

### 2.1 Tabla: FACTURAS

| Campo | Fuente Única | Sincronizado Desde | Actualizado En | Patrón |
|-------|--------------|-------------------|----------------|--------|
| `id` | SERIAL (autoinc) | - | DB auto | PRIMARY KEY |
| `numero_factura` | Proveedor/Sistema | API input | list_facturas() | NO cambia |
| `estado` | workflow_automatico.py | workflow.estado | _sincronizar_estado_factura() | AUTOSYNC |
| `responsable_id` | asignacion_nit | - | Asignación NIT | NO cambia |
| `accion_por` | **facturas.accion_por (BD)** | workflow.aprobada_por ó rechazada_por | _sincronizar_estado_factura() | **AUTOSYNC** |
| `aprobado_por` | workflow_aprobacion.aprobada_por | workflow | _sincronizar_estado_factura() | AUTOSYNC (deprecated) |
| `fecha_aprobacion` | workflow_aprobacion.fecha_aprobacion | workflow | _sincronizar_estado_factura() | AUTOSYNC |
| `rechazado_por` | workflow_aprobacion.rechazada_por | workflow | _sincronizar_estado_factura() | AUTOSYNC (deprecated) |

### 2.2 Tabla: WORKFLOW_APROBACION_FACTURAS

| Campo | Tipo | Generado Por | Sincronización |
|-------|------|--------------|-----------------|
| `aprobada_por` | VARCHAR(255) | **Usuario** (en aprobar_manual()) | → factura.accion_por |
| `rechazada_por` | VARCHAR(255) | **Usuario** (en rechazar()) | → factura.accion_por |
| `aprobada` | BOOLEAN | aprobar_manual() | → factura.estado |
| `rechazada` | BOOLEAN | rechazar() | → factura.estado |

---

## III. FLUJOS DE SINCRONIZACIÓN

### 3.1 Flujo: Aprobación Manual

```
┌─────────────────────────────────────────────────────────────┐
│ Usuario aprueba factura en dashboard (frontend)             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ POST /facturas/{id}/aprobar  │
        │ Body: {aprobado_por: "Juan"} │
        └────────────┬─────────────────┘
                     │
                     ▼
      ┌─────────────────────────────────────────┐
      │ WorkflowAutomaticoService.aprobar_manual()│
      │ (app/services/workflow_automatico.py)   │
      │                                         │
      │ 1. workflow.aprobada = true             │
      │ 2. workflow.aprobada_por = "Juan"       │
      │ 3. workflow.fecha_aprobacion = NOW()    │
      │ 4. db.commit()  ← TRANSACCIÓN 1        │
      └────────────┬────────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────────┐
    │ _sincronizar_estado_factura(workflow)       │
    │ (Automáticamente llamada después de approve) │
    │                                              │
    │ if workflow.aprobada:                       │
    │    factura.accion_por = workflow.aprobada_por│ ← AUTOSYNC
    │    factura.estado = "aprobada"              │ ← AUTOSYNC
    │    factura.aprobado_por = workflow.aprobada_por│ (deprecated)
    │    factura.fecha_aprobacion = workflow.fecha │
    │                                              │
    │ db.commit()  ← TRANSACCIÓN 2 (misma)        │
    └──────────────┬───────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────────┐
        │ Notificación enviada (opcional)      │
        │ (email_notifications.py)             │
        └──────────────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────────┐
    │ Dashboard lee /facturas/all              │
    │                                         │
    │ SELECT ... accion_por FROM facturas     │ ← Lee de BD
    │                                         │
    │ Retorna en FacturaRead schema:          │
    │ {                                       │
    │   "accion_por": "Juan",                 │ ← Desde DB
    │   "estado": "aprobada",                 │
    │   "responsable": "Juan Pérez"           │
    │ }                                       │
    └─────────────────────────────────────────┘
```

**PUNTOS CRÍTICOS:**
1. ✓ Usuario input: `aprobado_por = "Juan"`
2. ✓ Se escribe en `workflow.aprobada_por`
3. ✓ Se sincroni za automáticamente a `factura.accion_por`
4. ✓ Dashboard lee de `factura.accion_por` (BD)
5. ✓ TODO en una transacción atómica

### 3.2 Flujo: Rechazo

Mismo que aprobación, pero:
- `workflow.rechazada = true`
- `workflow.rechazada_por = "María"`
- `factura.accion_por = "María"` (sincronizado)

### 3.3 Flujo: Aprobación Automática

```
Sistema identifica que factura cumple criterios:
    ↓
_aprobar_automaticamente():
    - workflow.aprobada = true
    - workflow.aprobada_por = "SISTEMA_AUTO"
    ↓
_sincronizar_estado_factura():
    - factura.accion_por = "SISTEMA_AUTO"
    - factura.estado = "aprobada_auto"
    ↓
Dashboard muestra: accion_por = "SISTEMA DE AUTOMATIZACIÓN"
```

---

## IV. VERIFICACIÓN DE SINCRONIZACIÓN

### 4.1 En Código Python (Testing)

```python
# TEST: Verificar que accion_por se sincroniza
def test_accion_por_sincroniza():
    # BEFORE
    factura = db.query(Factura).get(1)
    assert factura.accion_por is None

    workflow = factura.workflow_history

    # ACT: Aprobar
    servicio.aprobar_manual(
        workflow_id=workflow.id,
        aprobado_por="Juan Pérez"
    )

    # AFTER: accion_por debe estar sincronizado
    db.refresh(factura)

    assert factura.accion_por == "Juan Pérez"  # ← VERIFICACIÓN
    assert factura.estado == EstadoFactura.aprobada
    assert workflow.aprobada_por == "Juan Pérez"
```

### 4.2 En BD (Manual Verification)

```sql
-- Verificar que accion_por está sincronizado
SELECT
    f.id,
    f.estado,
    f.accion_por,
    waf.aprobada_por,
    waf.rechazada_por,
    CASE
        WHEN waf.aprobada THEN 'Debería ser: ' + waf.aprobada_por
        WHEN waf.rechazada THEN 'Debería ser: ' + waf.rechazada_por
        ELSE 'No aprobada/rechazada'
    END AS esperado
FROM facturas f
LEFT JOIN workflow_aprobacion_facturas waf ON f.id = waf.factura_id
WHERE f.accion_por IS NOT NULL
LIMIT 10;

-- Verificar inconsistencias
SELECT
    f.id,
    f.accion_por,
    CASE
        WHEN waf.aprobada AND f.accion_por != waf.aprobada_por THEN 'ERROR: accion_por != aprobada_por'
        WHEN waf.rechazada AND f.accion_por != waf.rechazada_por THEN 'ERROR: accion_por != rechazada_por'
        ELSE 'OK'
    END AS status
FROM facturas f
LEFT JOIN workflow_aprobacion_facturas waf ON f.id = waf.factura_id
WHERE status = 'ERROR';
```

---

## V. CASOS ESPECIALES Y EXCEPCIONES

### 5.1 Facturas Antiguas (Pre-Sincronización)

```
Problema: Factura aprobada ANTES de que accion_por existiera
         accion_por = NULL, pero aprobada_por_workflow = "Juan"

Solución en Schema (fallback):
    if not accion_por and aprobado_por_workflow:
        accion_por = aprobado_por_workflow  # ← Fallback
```

### 5.2 Cambio de Responsable (Aunque sea poco probable)

```
NUNCA cambiar:
    factura.responsable_id  (asignación original)

PUEDES cambiar:
    accion_por  (quien aprobó)  - automáticamente
    estado      (estado actual)   - automáticamente
```

### 5.3 Corrección Manual de Datos

```
SI necesitas corregir datos en BD:

❌ NUNCA:
UPDATE facturas SET accion_por = 'Juan' WHERE id = 5;

 SIEMPRE:
1. Crear migración Alembic que documente el cambio
2. Incluir razón en comentario
3. Hacer reversible (downgrade)
4. Ejecutar después de merging (no antes)
```

---

## VI. MONITOREO Y ALERTAS

### 6.1 Query para Detectar Inconsistencias

```sql
-- Ejecutar DIARIAMENTE
SELECT
    f.id,
    f.numero_factura,
    f.accion_por,
    waf.aprobada_por,
    waf.rechazada_por,
    'Inconsistencia' AS alerta
FROM facturas f
LEFT JOIN workflow_aprobacion_facturas waf ON f.id = waf.factura_id
WHERE
    (f.estado = 'aprobada' AND f.accion_por IS NULL AND waf.aprobada = true)
    OR
    (f.estado = 'rechazada' AND f.accion_por IS NULL AND waf.rechazada = true)
    OR
    (waf.aprobada = true AND f.accion_por != waf.aprobada_por)
    OR
    (waf.rechazada = true AND f.accion_por != waf.rechazada_por);
```

**Si retorna resultados:** 🚨 **CRÍTICO - Inconsistencia detectada**

### 6.2 Metricas de Monitoreo

```python
# Agregar a health check endpoint
def get_data_integrity_metrics():
    """Retorna métricas de integridad de datos"""

    # Facturas sin accion_por que deberían tenerla
    inconsistent = db.query(Factura).filter(
        Factura.accion_por == None,
        Factura.estado.in_(['aprobada', 'rechazada'])
    ).count()

    return {
        "inconsistent_facturas": inconsistent,
        "status": "OK" if inconsistent == 0 else "ERROR",
        "message": f"{inconsistent} facturas sin accion_por"
    }
```

---

## VII. CHECKLIST PARA NUEVOS CAMPOS

Si necesitas agregar un nuevo campo que requiere sincronización:

- [ ] Campo agregado al modelo (source)
- [ ] Campo agregado al schema (output)
- [ ] Sincronización implementada en `_sincronizar_estado_factura()`
- [ ] Campo indexado en BD (si aplica)
- [ ] Test que valida la sincronización
- [ ] Migración Alembic creada
- [ ] Migración puebla datos históricos
- [ ] Documentación actualizada
- [ ] Validación pre-commit revisa campo
- [ ] Deployment checklist actualizado

---

## VIII. TROUBLESHOOTING

### Problema: accion_por está NULL pero factura está aprobada

```python
# DEBUG
factura = db.query(Factura).get(id)
print(f"accion_por: {factura.accion_por}")
print(f"estado: {factura.estado}")
print(f"aprobado_por_workflow: {factura.aprobado_por_workflow}")

# CAUSA PROBABLE
# 1. Factura aprobada ANTES de que accion_por existiera
#    → Aplicar migración que puebla datos históricos
#
# 2. Sincronización no se ejecutó
#    → Revisar que _sincronizar_estado_factura() se llama
#
# 3. BD no tiene la columna
#    → Ejecutar: alembic upgrade head
```

### Problema: accion_por tiene valor diferente a aprobada_por

```python
# DEBUG
workflow = factura.workflow_history
print(f"accion_por: {factura.accion_por}")
print(f"workflow.aprobada_por: {workflow.aprobada_por}")

# CAUSA PROBABLE
# 1. Dos usuarios aprobaron (¿multiple approvers?)
# 2. Manual update sin sincronización
# 3. Race condition en BD

# SOLUCIÓN
# → Revisar logs de auditoría
# → Crear migración que fija inconsistencia
# → Agregar constraint de BD que previene esto
```

---

## IX. REGLAS FINALES

🚨 **CRÍTICAS - No violar bajo ninguna circunstancia:**

1. **NUNCA** actualizar `accion_por` manualmente en BD
2. **NUNCA** desincronizar campos relacionados
3. **NUNCA** omitir transacción atómica en cambios relacionados
4. **NUNCA** agregar campo nuevo sin test de sincronización
5. **NUNCA** cambiar migración después de push a remoto

 **SIEMPRE:**
1. Ejecutar `validate_before_commit.py`
2. Usar `_sincronizar_estado_factura()` para cambios
3. Documentar en este archivo nuevos flujos
4. Incluir test que valida sincronización
5. Revisar BD después de deployment

---

**Última actualización:** 2025-10-22
**Nivel:** Enterprise / Fortune 500
**Responsable:** Senior Development Team

Preguntas: Consultar DEPLOYMENT_CHECKLIST_ENTERPRISE.md
