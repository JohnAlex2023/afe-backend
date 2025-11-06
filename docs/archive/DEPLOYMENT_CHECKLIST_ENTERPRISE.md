# DEPLOYMENT CHECKLIST - Enterprise Level

**⚠️ CRÍTICO: Usar este checklist ANTES de cada commit y deployment**

---

## FASE 1: PRE-COMMIT VALIDATION (Antes de git commit)

### 1.1 Ejecutar Validación Automática
```bash
python scripts/validate_before_commit.py
# Debe mostrar:  TODAS LAS VALIDACIONES PASARON
```

**Validaciones que ejecuta:**
- [ ] Migraciones Alembic en sync
- [ ] No hay código deprecated sin documentar
- [ ] Modelo ↔ Schema sincronizados
- [ ] Campos críticos sincronizados
- [ ] No hay imports circulares
- [ ] Tests existen para cambios críticos
- [ ] Sintaxis Python correcta

### 1.2 Verificar Cambios en Modelos

Si cambiaste algo en `app/models/`:

```bash
# 1. Verificar que cambios están sincronizados en schemas
grep -r "NOMBRE_CAMPO" app/schemas/

# 2. Verificar que el campo está documentado en ARQUITECTURA_*.md
cat ARQUITECTURA_*.md | grep -i "NOMBRE_CAMPO"

# 3. Crear test para el nuevo campo
# (Si no existe, crear antes de commit)
```

- [ ] Campo existe en modelo
- [ ] Campo está en schema correspondiente
- [ ] Campo está documentado
- [ ] Existe test para el campo
- [ ] No es campo deprecated

### 1.3 Verificar Migraciones Alembic

Si tocaste BD:

```bash
# Ver estado actual
alembic current

# Ver si hay cambios no aplicados
alembic status

# Verificar sintaxis de migraciones
alembic heads
# Debe mostrar: 1 head (no múltiples)
```

- [ ] No hay múltiples heads
- [ ] down_revision está correcto
- [ ] Migration usa sintaxis MySQL (no PostgreSQL)
- [ ] Upgrade function tiene try/except
- [ ] Downgrade function está implementada o documentada

### 1.4 Verificar Sincronización de Datos

Si cambios afectan datos:

```bash
# Verificar que los datos se sincronizan automáticamente
python scripts/validate_data_sync.py  # (si existe)

# O revisar manualmente que campos se sincronizan en:
grep -n "factura\." app/services/workflow_automatico.py | grep "="
```

- [ ] Sincronización está en `_sincronizar_estado_factura()`
- [ ] Sincronización es automática (no manual)
- [ ] Campo destino está nulleable en BD
- [ ] No hay hard-coded values (solo variables)

---

## FASE 2: GIT COMMIT (Antes de hacer commit)

### 2.1 Mensaje de Commit Profesional

Formato:
```
<tipo>: <descripción breve>

<descripción detallada>

Cambios:
- Punto 1
- Punto 2

Tests:
- ✓ Test 1 pass
- ✓ Test 2 pass

Validaciones:
- ✓ Migraciones en sync
- ✓ Schema actualizado
- ✓ Tests pass (X/Y)
```

**Tipos válidos:**
- `feat:` Nueva característica
- `fix:` Corrección de bug
- `refactor:` Refactorización sin cambios funcionales
- `test:` Agregar/actualizar tests
- `docs:` Cambios en documentación
- `chore:` Cambios en configuración/build

- [ ] Tipo correcto especificado
- [ ] Descripción clara (no vaga)
- [ ] Cambios listados explícitamente
- [ ] Tests mencionados
- [ ] Validaciones mencionadas

### 2.2 Antes de `git commit`

```bash
# 1. Ver EXACTAMENTE qué se va a commitear
git status
git diff --cached

# 2. Verificar archivos que NO deberían estar
git status | grep -E "(\.env|credentials|secret|password|token)"
# Debe estar VACÍO

# 3. Revisar que no hay archivos temporales
git status | grep -E "(\.pyc|__pycache__|\.tmp|\.swp)"
# Debe estar VACÍO

# 4. Revisar tamaño de archivos (no > 1MB)
git diff --cached --stat
```

- [ ] No hay `.env` en commit
- [ ] No hay credenciales
- [ ] No hay archivos temporales
- [ ] No hay cambios accidentales
- [ ] Archivos no son demasiado grandes

### 2.3 Hacer Commit

```bash
# Solo después de pasar todo lo anterior
git add -A
git commit -m "mensaje profesional"

# Verificar que committeó correctamente
git log -1 --stat
```

- [ ] Commit creado exitosamente
- [ ] Mensaje aparece en git log
- [ ] Archivos correctos en commit

---

## FASE 3: PRE-DEPLOYMENT (Antes de push/deploy)

### 3.1 Ejecutar Test Suite Completa

```bash
# Tests unitarios críticos
pytest tests/test_workflow_integrity.py -v

# Tests de sincronización de datos
pytest tests/test_accion_por_sync.py -v

# Tests de integridad general
pytest tests/ -k "integrity or sync" -v

# Todos los tests (opcional, toma más tiempo)
pytest tests/ -v --tb=short
```

- [ ] Todos los tests pasan (100%)
- [ ] No hay skipped tests
- [ ] No hay warnings críticos
- [ ] Tiempo de ejecución < 5 minutos

### 3.2 Ejecutar Linter y Formatter

```bash
# Verificar sintaxis
python -m pylint app/ --disable=C0111,C0103 --max-line-length=120

# Verificar imports
python -m isort --check-only --diff app/

# Verificar formatting
python -m black --check app/
```

- [ ] No hay errores de linting (E, F)
- [ ] Warnings son documentados
- [ ] Imports están organizados
- [ ] Código está formateado

### 3.3 Verificar que Servidor Inicia

```bash
# Terminal 1: Iniciar servidor
python -m uvicorn app.main:app --reload

# Terminal 2: Esperar a que diga "Application startup complete"
# Luego:
curl -s http://127.0.0.1:8000/docs | head -20
# Debe mostrar: <!DOCTYPE html> (API Docs)
```

- [ ] Servidor inicia sin errores
- [ ] Aplicación startup completa
- [ ] No hay excepciones en logs
- [ ] API docs accesible en /docs

### 3.4 Validar Integridad de BD

```bash
# Conectar a MySQL
mysql -u root -p -e "
USE afe_backend;

-- Verificar que columnas críticas existen
SHOW COLUMNS FROM facturas LIKE 'accion_por';
-- Debe mostrar: accion_por VARCHAR(255)

-- Verificar que datos están sincronizados
SELECT COUNT(*) FROM facturas WHERE accion_por IS NOT NULL AND estado IN ('aprobada', 'rechazada');
-- Debe mostrar: número > 0 (si hay facturas aprobadas)

-- Verificar consistencia
SELECT f.id, f.estado, f.accion_por, waf.aprobada_por, waf.rechazada_por
FROM facturas f
LEFT JOIN workflow_aprobacion_facturas waf ON f.id = waf.factura_id
WHERE f.accion_por IS NOT NULL
LIMIT 5;
-- Verificar que accion_por = aprobada_por O rechazada_por
"
```

- [ ] Columnas necesarias existen
- [ ] Datos están sincronizados
- [ ] No hay inconsistencias
- [ ] Integridad referencial OK

---

## FASE 4: DEPLOYMENT A PRODUCCIÓN

### 4.1 Último Checkpoint Antes de Push

```bash
# Ver cambios que se van a pushear
git log origin/main..HEAD --oneline

# Ver tamaño de cambios
git diff origin/main --stat

# Hacer un backup de BD (en prod)
# mysqldump -u root -p afe_backend > backup_$(date +%s).sql
```

- [ ] Cambios son los esperados
- [ ] No hay commits accidentales
- [ ] BD tiene backup (si aplica)

### 4.2 Push a Repositorio

```bash
# Push solo si TODAS las fases anteriores pasaron
git push origin main

# Verificar que push fue exitoso
git log origin/main -1
```

- [ ] Push completado exitosamente
- [ ] Commits aparecen en origen
- [ ] CI/CD pipeline inicia (si configu rado)

### 4.3 Deployment a Servidor

```bash
# En servidor de producción:

# 1. Pull cambios
cd /path/to/afe-backend
git pull origin main

# 2. Instalar dependencias nuevas
pip install -r requirements.txt --upgrade

# 3. Ejecutar migraciones (SI APLICA)
alembic upgrade head

# 4. Verificar que server inicia
systemctl restart afe-backend
journalctl -u afe-backend -f

# 5. Smoke test
curl -s http://prod-server/api/health | jq .
```

- [ ] Git pull exitoso
- [ ] Dependencias instaladas
- [ ] Migraciones aplicadas
- [ ] Servidor inicia sin errores
- [ ] Health check responde OK

### 4.4 Post-Deployment Validation

```bash
# 1. Verificar logs por errores
journalctl -u afe-backend -p err -n 20

# 2. Verificar BD está íntegra
SELECT COUNT(*) FROM facturas WHERE accion_por IS NULL AND estado IN ('aprobada', 'rechazada');
# Debe mostrar: 0 (ninguna inconsistencia)

# 3. Verificar API endpoints responden
curl -s http://prod-server/api/v1/facturas | jq '.length'

# 4. Revisar métricas de performance
curl http://prod-server/metrics | grep http_request_duration
```

- [ ] No hay errores en logs
- [ ] BD es consistente
- [ ] API endpoints responden
- [ ] Performance es aceptable

---

## MATRIZ DE RIESGOS Y MITIGACIONES

| Cambio | Riesgo | Mitigación |
|--------|--------|-----------|
| Agregar campo en modelo | BD desincronizada | Crear migración Alembic + test |
| Cambiar sincronización | Datos inconsistentes | Ejecutar `validate_before_commit.py` |
| Cambiar schema | API retorna valores incorrectos | Verificar test schema + test integration |
| Cambiar DB schema | Consultas fallan | Ejecutar alembic status + validation |

---

## REGLAS DE ORO (CRÍTICAS)

🚨 **NUNCA hacer un commit sin:**
1. ✓ Pasar `validate_before_commit.py`
2. ✓ Tests pasan (100%)
3. ✓ Servidor inicia sin errores
4. ✓ Checklist de integridad BD pasado
5. ✓ Mensaje de commit profesional

🚨 **NUNCA hacer un deployment sin:**
1. ✓ Commit validado + tests pass
2. ✓ Backup de BD (si aplica)
3. ✓ Todos los pasos de FASE 4 completados
4. ✓ Validación post-deployment exitosa

---

## AUTOMATIZACIÓN RECOMENDADA

```bash
# .git/hooks/pre-commit (crear este archivo)
#!/bin/bash
python scripts/validate_before_commit.py || exit 1
pytest tests/test_accion_por_sync.py tests/test_workflow_integrity.py || exit 1
exit 0
```

```bash
# Hacer ejecutable
chmod +x .git/hooks/pre-commit
```

Así el commit fallará automáticamente si validaciones no pasan.

---

## CONTACTO EN CASO DE ERROR

Si durante deployment ocurre error:

1. **STOP** - No continuar
2. **ROLLBACK** - Revertir último commit
3. **ANALYZE** - Revisar qué falló
4. **FIX** - Arreglar en development
5. **RETRY** - Desde FASE 1

```bash
# Rollback rápido
git revert HEAD  # Revierte cambios
git push origin main

# O si no está en remoto:
git reset --hard HEAD~1
```

---

**Última actualización:** 2025-10-22
**Nivel:** Enterprise / Fortune 500
**Responsable:** Senior Development Team
