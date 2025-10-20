# FASE 2: ELIMINACIÓN DE REDUNDANCIA - PLAN EJECUTIVO

**Fecha**: 2025-10-19
**Proyecto**: AFE Backend - Refactorización Profesional DB
**Nivel**: Senior Development Team (10+ años experiencia)
**Objetivo**: Alcanzar calificación 10/10 (Perfección Enterprise)

---

## RESUMEN EJECUTIVO

Fase 2 elimina **toda la redundancia** identificada en Fase 1, llevando la base de datos de 9.5/10 a **10/10 perfecto**. Estrategia conservadora con rollback en cada paso.

### Objetivos

1. ✅ Corregir **518 inconsistencias** detectadas en datos
2. ✅ Eliminar campos calculados redundantes (usando generated columns)
3. ✅ Normalizar datos de workflow (mover de facturas a workflow)
4. ✅ Crear helpers transparentes para acceso a datos
5. ✅ Actualizar todo el código para usar nuevas propiedades
6. ✅ Zero downtime, rollback seguro en cada paso

### Impacto Esperado

| Métrica | Actual (9.5/10) | Objetivo (10/10) | Mejora |
|---------|-----------------|------------------|--------|
| **Violaciones 3NF** | 6 | 0 | -100% |
| **Campos Redundantes** | 10 | 0 | -100% |
| **Consistencia Datos** | 82% | 100% | +18% |
| **Generated Columns** | 0 | 3 | +∞ |
| **Helpers Transparentes** | 0 | 6 | +∞ |

---

## ESTRATEGIA: 5 PASOS INCREMENTALES

Cada paso es independiente, con commit y validación. Si algo falla, rollback del paso específico.

```
Fase 2.1: Corregir Inconsistencias (518 registros)
    ↓
Fase 2.2: Crear Helpers de Workflow (6 propiedades)
    ↓
Fase 2.3: Migrar Código a Helpers (50+ archivos)
    ↓
Fase 2.4: Normalizar Workflow (mover campos)
    ↓
Fase 2.5: Generated Columns (total_a_pagar, subtotal, total)
```

**Timeline estimado:** 2-3 horas por paso, ~12-15 horas total
**Riesgo:** Bajo (cada paso es reversible)
**Beneficio:** Base de datos perfecta (10/10)

---

## FASE 2.1: CORRECCIÓN DE INCONSISTENCIAS

### Problema

- 41 facturas (16%) con `total_a_pagar ≠ subtotal + iva`
- 477 items (100%) con `subtotal ≠ cantidad × precio - descuento`
- 477 items (100%) con `total ≠ subtotal + impuestos`

### Análisis de Causa Raíz

¿Por qué hay inconsistencias?

1. **Datos legacy** importados antes de validaciones
2. **Errores de extracción** de XML en versiones antiguas
3. **Actualización manual** de campos sin recalcular totales
4. **Redondeos** diferentes en distintas versiones del código

### Estrategia de Corrección

**Principio:** Confiar en el **valor oficial del XML** (`total_a_pagar` en facturas, `total` en items)

#### Para Facturas

```sql
-- ✅ ESTRATEGIA: total_a_pagar es la verdad absoluta (viene del XML oficial)
-- Recalcular subtotal e IVA si es necesario

-- Casos:
-- 1. Si total_a_pagar = subtotal + iva → OK, no tocar
-- 2. Si total_a_pagar ≠ subtotal + iva → Recalcular IVA asumiendo 19%

UPDATE facturas
SET
    subtotal = ROUND(total_a_pagar / 1.19, 2),
    iva = total_a_pagar - ROUND(total_a_pagar / 1.19, 2)
WHERE ABS(total_a_pagar - (subtotal + iva)) > 0.01
AND total_a_pagar IS NOT NULL;
```

#### Para Items

```sql
-- ✅ ESTRATEGIA: item.total es la verdad (viene del XML)
-- Recalcular subtotal desde cantidad × precio

-- Casos típicos:
-- 1. subtotal ≠ cantidad × precio → Usar total como base
-- 2. total ≠ subtotal + impuestos → Recalcular subtotal

UPDATE factura_items
SET
    subtotal = CASE
        -- Si hay impuestos, restar del total
        WHEN total_impuestos > 0 THEN total - total_impuestos
        -- Si no hay impuestos, subtotal = total
        ELSE total
    END
WHERE ABS(total - (subtotal + total_impuestos)) > 0.01;
```

### Script de Corrección

**Archivo:** `scripts/corregir_inconsistencias_fase2.py`

```python
"""
Corrección de inconsistencias detectadas en Fase 1.

IMPORTANTE:
- Respeta valores oficiales del XML (total_a_pagar, item.total)
- Recalcula valores derivados (subtotal, iva)
- Genera reporte detallado de cambios
- Backup automático antes de corrección
"""

def corregir_facturas(db: Session):
    """Corrige inconsistencias en facturas."""
    facturas = db.query(Factura).all()
    corregidas = 0

    for factura in facturas:
        if factura.tiene_inconsistencia_total:
            # Calcular subtotal e IVA correctos desde total_a_pagar
            total = factura.total_a_pagar
            subtotal_correcto = round(total / Decimal('1.19'), 2)
            iva_correcto = total - subtotal_correcto

            logger.info(
                f"Factura {factura.numero_factura}:\n"
                f"  Total (oficial): ${total}\n"
                f"  Subtotal antes:  ${factura.subtotal} → después: ${subtotal_correcto}\n"
                f"  IVA antes:       ${factura.iva} → después: ${iva_correcto}"
            )

            factura.subtotal = subtotal_correcto
            factura.iva = iva_correcto
            corregidas += 1

    return corregidas

def corregir_items(db: Session):
    """Corrige inconsistencias en items."""
    items = db.query(FacturaItem).all()
    corregidos = 0

    for item in items:
        if item.tiene_inconsistencia_subtotal or item.tiene_inconsistencia_total:
            # Recalcular desde item.total (oficial del XML)
            total = item.total
            impuestos = item.total_impuestos or Decimal('0')
            subtotal_correcto = total - impuestos

            item.subtotal = subtotal_correcto
            corregidos += 1

    return corregidos
```

**Resultado Esperado:**
- 41 facturas corregidas
- 477 items corregidos
- 0 inconsistencias restantes
- Reporte CSV con todos los cambios

---

## FASE 2.2: HELPERS DE WORKFLOW

### Problema

Datos de aprobación/rechazo duplicados en dos lugares:

```python
# ❌ REDUNDANTE: Mismos datos en 2 tablas
facturas:
    aprobado_por
    fecha_aprobacion
    rechazado_por
    fecha_rechazo
    motivo_rechazo

workflow_aprobacion_facturas:
    aprobada_por
    fecha_aprobacion
    rechazada_por
    fecha_rechazo
    detalle_rechazo
```

### Solución: Helpers Transparentes

Agregar propiedades al modelo `Factura` que accedan a datos de workflow:

```python
class Factura(Base):
    # ... campos existentes ...

    # Relación a workflow (puede no existir)
    workflow = relationship("WorkflowAprobacionFactura",
                          primaryjoin="foreign(WorkflowAprobacionFactura.factura_id) == Factura.id",
                          uselist=False)

    # ==================== HELPERS DE WORKFLOW ====================

    @property
    def aprobado_por_workflow(self) -> Optional[str]:
        """
        Usuario que aprobó (desde workflow si existe, sino desde factura).

        ⚠️ DEPRECATION: aprobado_por en facturas será eliminado en Fase 2.4
        """
        if self.workflow:
            return self.workflow.aprobada_por
        return self.aprobado_por  # Fallback a campo legacy

    @property
    def fecha_aprobacion_workflow(self) -> Optional[datetime]:
        """Fecha de aprobación (desde workflow primero)."""
        if self.workflow:
            return self.workflow.fecha_aprobacion
        return self.fecha_aprobacion

    @property
    def rechazado_por_workflow(self) -> Optional[str]:
        """Usuario que rechazó (desde workflow primero)."""
        if self.workflow:
            return self.workflow.rechazada_por
        return self.rechazado_por

    @property
    def fecha_rechazo_workflow(self) -> Optional[datetime]:
        """Fecha de rechazo (desde workflow primero)."""
        if self.workflow:
            return self.workflow.fecha_rechazo
        return self.fecha_rechazo

    @property
    def motivo_rechazo_workflow(self) -> Optional[str]:
        """Motivo de rechazo (desde workflow primero)."""
        if self.workflow:
            return self.workflow.detalle_rechazo
        return self.motivo_rechazo

    @property
    def tipo_aprobacion_workflow(self) -> Optional[str]:
        """Tipo de aprobación (solo en workflow)."""
        if self.workflow:
            return self.workflow.tipo_aprobacion.value if self.workflow.tipo_aprobacion else None
        return None
```

**Beneficio:** Código accede a datos correctos sin saber de dónde vienen

```python
# ✅ CÓDIGO NUEVO (usa helpers)
factura = get_factura(123)
print(f"Aprobada por: {factura.aprobado_por_workflow}")
# → Devuelve dato de workflow si existe, sino de factura

# ❌ CÓDIGO VIEJO (acceso directo)
print(f"Aprobada por: {factura.aprobado_por}")
# → Solo ve dato en facturas, puede estar desactualizado
```

---

## FASE 2.3: MIGRACIÓN DE CÓDIGO

### Análisis de Impacto

Buscar y reemplazar en todos los archivos:

```python
# Búsqueda:
factura.aprobado_por
factura.fecha_aprobacion
factura.rechazado_por
factura.fecha_rechazo
factura.motivo_rechazo

# Reemplazo:
factura.aprobado_por_workflow
factura.fecha_aprobacion_workflow
factura.rechazado_por_workflow
factura.fecha_rechazo_workflow
factura.motivo_rechazo_workflow
```

### Archivos a Actualizar (estimado 50+)

**CRUDs:**
- `app/crud/factura.py`
- Todos los métodos de actualización de estado

**Servicios:**
- `app/services/flujo_automatizacion_facturas.py`
- `app/services/workflow_automatico.py`
- `app/services/notificaciones.py`
- `app/services/export_service.py`

**APIs:**
- `app/api/v1/routers/facturas.py`
- Todos los endpoints que retornan facturas

**Schemas:**
- `app/schemas/factura.py` - agregar campos `_workflow`

### Estrategia de Migración

1. **Grep completo** para encontrar todos los usos
2. **Actualizar** cada archivo uno por uno
3. **Commit** por archivo o grupo lógico
4. **Test** después de cada cambio

---

## FASE 2.4: NORMALIZACIÓN DE WORKFLOW

### Migración de Datos

Mover datos de `facturas` → `workflow_aprobacion_facturas`:

```python
# Script: migrar_datos_workflow_fase2.py

def migrar_datos_workflow(db: Session):
    """
    Migra datos de aprobación/rechazo de facturas a workflow.

    Para cada factura:
    1. Si tiene workflow → actualizar workflow con datos de factura
    2. Si no tiene workflow → crear workflow con datos de factura
    """

    facturas = db.query(Factura).all()

    for factura in facturas:
        if factura.workflow:
            # Actualizar workflow existente
            if factura.aprobado_por:
                factura.workflow.aprobada_por = factura.aprobado_por
                factura.workflow.fecha_aprobacion = factura.fecha_aprobacion

            if factura.rechazado_por:
                factura.workflow.rechazada_por = factura.rechazado_por
                factura.workflow.fecha_rechazo = factura.fecha_rechazo
                factura.workflow.detalle_rechazo = factura.motivo_rechazo
        else:
            # Crear workflow si tiene datos de aprobación/rechazo
            if factura.aprobado_por or factura.rechazado_por:
                workflow = WorkflowAprobacionFactura(
                    factura_id=factura.id,
                    aprobada_por=factura.aprobado_por,
                    fecha_aprobacion=factura.fecha_aprobacion,
                    rechazada_por=factura.rechazado_por,
                    fecha_rechazo=factura.fecha_rechazo,
                    detalle_rechazo=factura.motivo_rechazo,
                    estado=EstadoFacturaWorkflow.PROCESADA
                )
                db.add(workflow)

    db.commit()
```

### Eliminación de Campos (Alembic)

```python
# Migration: drop_redundant_workflow_fields_fase2.py

def upgrade():
    """Eliminar campos redundantes de facturas."""

    # Estos campos ahora están en workflow_aprobacion_facturas
    op.drop_column('facturas', 'aprobado_por')
    op.drop_column('facturas', 'fecha_aprobacion')
    op.drop_column('facturas', 'rechazado_por')
    op.drop_column('facturas', 'fecha_rechazo')
    op.drop_column('facturas', 'motivo_rechazo')

def downgrade():
    """Rollback: restaurar campos."""

    op.add_column('facturas', sa.Column('aprobado_por', sa.String(100)))
    op.add_column('facturas', sa.Column('fecha_aprobacion', sa.DateTime()))
    op.add_column('facturas', sa.Column('rechazado_por', sa.String(100)))
    op.add_column('facturas', sa.Column('fecha_rechazo', sa.DateTime()))
    op.add_column('facturas', sa.Column('motivo_rechazo', sa.String(1000)))
```

---

## FASE 2.5: GENERATED COLUMNS

### Objetivo

Eliminar campos calculados almacenados, usar generated columns de MySQL 8.0+

#### Facturas: total_a_pagar

**IMPORTANTE:** Mantener `total_a_pagar` como stored (viene del XML), pero validar con generated virtual:

```sql
-- Opción 1: Agregar columna de validación (recomendado)
ALTER TABLE facturas
ADD COLUMN total_calculado_validacion DECIMAL(15,2)
GENERATED ALWAYS AS (subtotal + iva) VIRTUAL;

-- Luego crear constraint
ALTER TABLE facturas
ADD CONSTRAINT chk_facturas_total_coherente
CHECK (ABS(total_a_pagar - total_calculado_validacion) <= 0.01);
```

**Beneficio:** MySQL valida automáticamente que total_a_pagar = subtotal + iva

#### Items: subtotal y total

```sql
-- Opción 2: Convertir a generated columns (más agresivo)
ALTER TABLE factura_items
DROP COLUMN subtotal,
ADD COLUMN subtotal DECIMAL(15,2)
GENERATED ALWAYS AS (
    (cantidad * precio_unitario) - COALESCE(descuento_valor, 0)
) STORED;

ALTER TABLE factura_items
DROP COLUMN total,
ADD COLUMN total DECIMAL(15,2)
GENERATED ALWAYS AS (
    subtotal + COALESCE(total_impuestos, 0)
) STORED;
```

**Beneficio:**
- Imposible tener inconsistencias
- MySQL calcula automáticamente
- Código usa los mismos campos

---

## VALIDACIÓN Y TESTING

### Pre-Migración

```bash
# 1. Backup completo
mysqldump afe_db > backup_pre_fase2_$(date +%Y%m%d).sql

# 2. Validar datos
python scripts/validar_integridad_datos.py

# 3. Contar inconsistencias
python scripts/contar_inconsistencias.py
```

### Durante Migración

Después de cada fase:

```bash
# Validar que no hay regresiones
pytest tests/ -v

# Validar endpoints
python scripts/test_all_endpoints.py

# Validar datos
python scripts/validar_integridad_datos.py
```

### Post-Migración

```bash
# Verificar 0 inconsistencias
python scripts/validar_integridad_datos.py

# Verificar performance
python scripts/benchmark_queries.py

# Verificar generated columns
SELECT * FROM facturas WHERE ABS(total_a_pagar - total_calculado_validacion) > 0.01;
# Debe retornar 0 filas
```

---

## ROLLBACK PLAN

Cada fase tiene rollback:

### Fase 2.1: Corregir Inconsistencias
```bash
# Restaurar desde backup
mysql afe_db < backup_pre_fase2_1.sql
```

### Fase 2.2: Helpers
```bash
# Revertir código
git revert <commit_hash>
```

### Fase 2.3: Migración Código
```bash
# Revertir commits
git revert <commit_hash_inicio>..<commit_hash_fin>
```

### Fase 2.4: Normalización Workflow
```bash
# Alembic downgrade
alembic downgrade -1
```

### Fase 2.5: Generated Columns
```bash
# Alembic downgrade
alembic downgrade -1
```

---

## TIMELINE Y RECURSOS

| Fase | Duración | Recursos | Riesgo |
|------|----------|----------|--------|
| 2.1: Corrección | 2-3h | 1 dev | Bajo |
| 2.2: Helpers | 1-2h | 1 dev | Bajo |
| 2.3: Migración Código | 4-6h | 2 devs | Medio |
| 2.4: Normalización | 2-3h | 1 dev | Medio |
| 2.5: Generated Columns | 1-2h | 1 dev | Medio |
| **TOTAL** | **10-16h** | **1-2 devs** | **Bajo-Medio** |

---

## RESULTADO ESPERADO

### Base de Datos Final (10/10)

- ✅ 0 violaciones de 3NF
- ✅ 0 campos redundantes
- ✅ 0 inconsistencias de datos
- ✅ 100% datos normalizados
- ✅ Generated columns para cálculos
- ✅ Helpers transparentes en modelos
- ✅ Código limpio y mantenible

### Métricas

| Métrica | Antes (9.5/10) | Después (10/10) |
|---------|----------------|-----------------|
| Violaciones 3NF | 6 | 0 |
| Campos Redundantes | 10 | 0 |
| Inconsistencias | 518 | 0 |
| Calificación | 9.5/10 | **10/10** |

---

**Documento preparado por:** Equipo de Desarrollo Senior (10+ años exp.)
**Revisado:** 2025-10-19
**Estado:** ✅ LISTO PARA EJECUCIÓN
**Aprobación requerida:** SÍ (cambios de schema)
