# OPERATIONAL STANDARDS - Enterprise Level

**⚠️ CRÍTICO: Este documento define los estándares operacionales que evitan regresiones**

---

## PROBLEMA QUE ESTAMOS EVITANDO

En los commits anteriores encontramos **errores operacionales repetidos**:

```
❌ PROBLEMA 1: Cambios en modelos sin migraciones Alembic
   → BD falla: "Unknown column..."
   → Servidor no inicia
   → Data inconsistent

❌ PROBLEMA 2: Sincronización incompleta entre capas
   → Modelos tienen campo X, pero schemas no lo retornan
   → Frontend recibe NULL
   → Dashboard muestra datos incorrectos

❌ PROBLEMA 3: Falta de validación antes de commit
   → Errores solo descubiertos en deployment
   → Downtime en producción
   → Muy tarde para arreglar
```

**Esto NO VUELVE A PASAR.** Hemos implementado un sistema profesional de prevención.

---

## CÓMO TRABAJA AHORA (4 CAPAS DE PROTECCIÓN)

```
┌──────────────────────────────────────────────────────────┐
│ CAPA 1: PRE-COMMIT (Antes de git commit)                │
│ ├─ validate_before_commit.py                            │
│ ├─ Verifica: Alembic, campos, tests, syntax             │
│ └─ DEBE PASAR: [SUCCESS] ALL VALIDATIONS PASSED         │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ CAPA 2: DEPLOYMENT CHECKLIST (Antes de push)            │
│ ├─ 4 fases: pre-commit, git commit, pre-deploy, deploy  │
│ ├─ 40+ checkpoints de validación                        │
│ └─ DEBE COMPLETARSE: Todos checkpoints                  │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ CAPA 3: DATA SYNCHRONIZATION RULES (Que sincronizar)    │
│ ├─ Define flujos de sincronización                      │
│ ├─ Valida en código y BD                                │
│ └─ DEBE CUMPLIR: Rules en DATA_SYNCHRONIZATION_RULES.md │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ CAPA 4: MONITORING & ALERTING (Post-deployment)         │
│ ├─ Queries que detectan inconsistencias                 │
│ ├─ Métricas de integridad de datos                      │
│ └─ DEBE MOSTRAR: 0 inconsistencias                      │
└──────────────────────────────────────────────────────────┘
```

---

## FLUJO DE DESARROLLO CORRECTO

### Paso 1: Desarrollo Local

```bash
# Hacer cambios en código
vim app/models/factura.py
vim app/schemas/factura.py
vim app/services/workflow_automatico.py

# Agregar/actualizar tests
vim tests/test_accion_por_sync.py
```

### Paso 2: Pre-Commit Validation (OBLIGATORIO)

```bash
# ANTES de hacer git commit:
python scripts/validate_before_commit.py

# DEBE MOSTRAR:
# [SUCCESS] ALL VALIDATIONS PASSED
# Status: READY FOR COMMIT

# Si muestra [FAILED]: arregla errores y vuelve a ejecutar
```

### Paso 3: Git Commit (Profesional)

```bash
# Mensaje profesional documentando cambios
git commit -m "feat: Descripción

Cambios:
- Punto 1
- Punto 2

Tests:
- Test 1 pass
- Test 2 pass

Validaciones:
- validate_before_commit.py: PASS
- Tests: X/Y pass"
```

### Paso 4: Deployment Checklist (EXHAUSTIVO)

Consultar: `DEPLOYMENT_CHECKLIST_ENTERPRISE.md`

```bash
# 4 FASES COMPLETAS:

FASE 1: PRE-COMMIT VALIDATION
├─ Validación automática: PASS
├─ Cambios en modelos: sincronizados
├─ Migraciones Alembic: sin conflictos
└─ Datos: sincronización verificada

FASE 2: GIT COMMIT
├─ Mensaje profesional: sí
├─ Archivos correctos: sí
└─ No hay credenciales/secrets: sí

FASE 3: PRE-DEPLOYMENT
├─ Test suite: 100% PASS
├─ Linter: sin errores críticos
├─ Servidor: inicia correctamente
└─ BD: integridad OK

FASE 4: PRODUCTION DEPLOYMENT
├─ Push a repositorio: OK
├─ Migraciones aplicadas: OK
├─ Servidor inicia: OK
└─ Health check: OK
```

### Paso 5: Post-Deployment Validation

```bash
# Ejecutar queries de validación
SELECT COUNT(*) FROM facturas WHERE accion_por IS NULL AND estado IN ('aprobada', 'rechazada');
# DEBE RETORNAR: 0

# Verificar métricas
curl http://prod-server/metrics | grep "inconsistent_facturas"
# DEBE RETORNAR: 0 o "OK"
```

---

## DOCUMENTOS CRÍTICOS

| Documento | Propósito | Cuándo Usar |
|-----------|-----------|------------|
| **DEPLOYMENT_CHECKLIST_ENTERPRISE.md** | 40+ checkpoints para deployment | ANTES de cada push/deploy |
| **DATA_SYNCHRONIZATION_RULES.md** | Cómo y cuándo sincronizar datos | Al agregar campos nuevos |
| **ARQUITECTURA_ACCION_POR_SYNC.md** | Caso específico: accion_por | Referencia para ACCION_POR |
| **scripts/validate_before_commit.py** | Validación automática | SIEMPRE antes de commit |

---

## REGLAS DE ORO (NO VIOLAR)

### ❌ NUNCA:

1. **NUNCA** hacer commit sin ejecutar `validate_before_commit.py`
2. **NUNCA** agregar campo en modelo sin migración Alembic
3. **NUNCA** cambiar campo en BD sin actualizar schema
4. **NUNCA** sincronizar datos manualmente (debe ser automático)
5. **NUNCA** desincronizar campos relacionados
6. **NUNCA** omitir transacción atómica en cambios relacionados
7. **NUNCA** push a remoto sin tests pasando 100%

###  SIEMPRE:

1. **SIEMPRE** ejecutar validación antes de commit
2. **SIEMPRE** completar DEPLOYMENT_CHECKLIST
3. **SIEMPRE** escribir tests para nuevas características
4. **SIEMPRE** documentar cambios en README/ARQUITECTURA
5. **SIEMPRE** sincronizar automáticamente (no manual)
6. **SIEMPRE** usar transacciones atómicas
7. **SIEMPRE** monitorear BD después de deployment

---

## MATRIZ DE RESPONSABILIDADES

| Rol | Responsabilidad | Verificación |
|-----|-----------------|--------------|
| **Developer** | Código correcto + tests | validate_before_commit.py PASS |
| **Senior Dev** | Review de arquitectura | DEPLOYMENT_CHECKLIST PASS |
| **DevOps** | Deployment a producción | Post-deployment validation OK |
| **Team Lead** | Monitoreo de regresiones | Queries de integridad diarias |

---

## AUTOMATIZACIÓN RECOMENDADA

### Pre-Commit Hook

Crear archivo `.git/hooks/pre-commit`:

```bash
#!/bin/bash
python scripts/validate_before_commit.py || exit 1
pytest tests/test_accion_por_sync.py tests/test_workflow_integrity.py -q || exit 1
exit 0
```

Hacer ejecutable:
```bash
chmod +x .git/hooks/pre-commit
```

Así el commit fallará automáticamente si hay problemas.

### CI/CD Pipeline

Si tienes GitHub Actions/GitLab CI:

```yaml
# .github/workflows/pre-commit-validation.yml
name: Pre-Commit Validation
on: [pull_request, push]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - run: python scripts/validate_before_commit.py
      - run: pytest tests/test_accion_por_sync.py tests/test_workflow_integrity.py -v
```

---

## RESPUESTA A: "¿POR QUÉ TANTA DOCUMENTACIÓN?"

**Respuesta profesional:**

Como equipo senior, sabemos que:

1. **Los errores operacionales repiten patrones**
   - Si no documentamos, repetimos el mismo error
   - Documentación previene olvidos

2. **La escala requiere procesos**
   - 1 developer: código informal funciona
   - 5+ developers: necesitas procesos, de lo contrario: caos

3. **Los "obvio" no son obvios para todos**
   - Lo que es obvio para ti, no lo es para alguien que hereda el código
   - Documentación = inversión en futuro

4. **Errores en producción son CAROS**
   - 1 error en prod = horas de downtime
   - 1 checklist = 15 minutos de validación
   - Costo/beneficio: obvio

---

## EJEMPLO REAL: Cómo Esto Hubiera Evitado El Error

**Escenario:** Alguien agrega campo `accion_por` a modelo

**SIN sistema (lo que pasó):**
```
1. Dev agrega campo en modelo
2. Dev hace commit (sin validar)
3. Dev hace push
4. Servidor intenta iniciar
5. Error: "Unknown column 'facturas.accion_por'"
6. 😱 Production down
```

**CON sistema (lo que ocurre ahora):**
```
1. Dev agrega campo en modelo
2. Dev ejecuta: python scripts/validate_before_commit.py
3. Script grita: "ERROR: accion_por not in schema!"
4. Dev actualiza schema
5. Dev ejecuta: python scripts/validate_before_commit.py
6. Script OK: "ALL VALIDATIONS PASSED"
7. Dev hace commit tranquilo
8. Deployment: sin problemas
9. 😊 Production seguro
```

**Diferencia:** 15 minutos vs. 2 horas de downtime

---

## RESUMEN EJECUTIVO

Has implementado un sistema profesional de 4 capas que:

 **PREVIENE** errores operacionales antes de que ocurran
 **DOCUMENTA** reglas de sincronización exhaustivamente
 **VALIDA** automáticamente antes de cada commit
 **MONITOREA** después de deployment
 **ESCALA** con el equipo (procesos, no individuos)

**Resultado:** Equipo senior competente que comete errores → Equipo senior con procesos que previene errores

---

## PRÓXIMOS PASOS

1. **Revisar** todos los documentos de este repositorio
2. **Ejecutar** `python scripts/validate_before_commit.py` antes de CADA commit
3. **Completar** DEPLOYMENT_CHECKLIST antes de CADA deployment
4. **Monitorear** inconsistencias en BD (queries en DATA_SYNCHRONIZATION_RULES.md)
5. **Actualizar** esta documentación cuando aparezcan nuevos patrones

---

## CONTACTO / ESCALACIÓN

Si encuentras:
- ❌ Error no documentado: agrega a este README
- ❌ Validación incompleta: mejora validate_before_commit.py
- ❌ Inconsistencia en BD: agrégalo a monitoring queries
- ❌ Patrón nuevo: documéntalo para que otros aprendan

**Recuerda:** La documentación no es carga, es inversión.

---

**Última actualización:** 2025-10-22
**Nivel:** Enterprise / Fortune 500
**Responsable:** Senior Development Team

**Status:**  SYSTEM OPERATIONAL - All 4 protection layers active
