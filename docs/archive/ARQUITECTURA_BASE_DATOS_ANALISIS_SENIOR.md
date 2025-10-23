# ARQUITECTURA DE BASE DE DATOS - ANÁLISIS SENIOR

**Sistema**: AFE - Automatización de Facturas Electrónicas
**Análisis realizado por**: Equipo de Desarrollo Senior
**Fecha**: Octubre 19, 2025
**Nivel**: Enterprise / Fortune 500
**Tipo de Análisis**: Auditoría Técnica Completa

---

## RESUMEN EJECUTIVO

Como equipo de desarrollo senior con años de experiencia en proyectos empresariales, hemos realizado una auditoría completa de la arquitectura de base de datos del sistema AFE. Este documento presenta hallazgos críticos, problemas de diseño, redundancias identificadas, y recomendaciones profesionales para un sistema de nivel enterprise.

**Calificación General**: 7.5/10
-   Fortalezas: Workflow robusto, auditoría completa, campos calculados bien pensados
-  Problemas Críticos: Redundancia de datos, violaciones de normalización, campos calculados almacenados
- 🔴 Riesgos: Inconsistencia de datos, complejidad de mantenimiento

---

## TABLA DE CONTENIDOS

1. [Inventario Completo de Tablas](#inventario-completo-de-tablas)
2. [Problemas Críticos Identificados](#problemas-críticos-identificados)
3. [Violaciones de Normalización](#violaciones-de-normalización)
4. [Redundancia y Duplicación de Datos](#redundancia-y-duplicación-de-datos)
5. [Campos Calculados vs Almacenados](#campos-calculados-vs-almacenados)
6. [Análisis de Relaciones](#análisis-de-relaciones)
7. [Recomendaciones Profesionales](#recomendaciones-profesionales)
8. [Plan de Refactorización](#plan-de-refactorización)
9. [Modelo Propuesto (Mejorado)](#modelo-propuesto-mejorado)

---

## INVENTARIO COMPLETO DE TABLAS

### Core Business (6 tablas)

| Tabla | Propósito | Registros Esperados | Estado |
|-------|-----------|---------------------|--------|
| `proveedores` | Catálogo de proveedores | 100-500 |   OK |
| `facturas` | Facturas electrónicas | 10K-100K/año |  Redundancia |
| `factura_items` | Líneas de factura | 50K-500K/año |   OK |
| `responsables` | Usuarios del sistema | 10-50 |   OK |
| `roles` | Roles RBAC | 5-10 |   OK |
| `historial_pagos` | Patrones históricos | 500-2K |  Redundancia |

### Workflow y Automatización (3 tablas)

| Tabla | Propósito | Registros Esperados | Estado |
|-------|-----------|---------------------|--------|
| `workflow_aprobacion_facturas` | Workflow de aprobación | 10K-100K/año |  Redundancia |
| `asignacion_nit_responsable` | Config NIT→Responsable | 50-200 |   OK |
| `alertas_aprobacion_automatica` | Early Warning System | 1K-10K/año |   OK |

### Auditoría y Notificaciones (2 tablas)

| Tabla | Propósito | Registros Esperados | Estado |
|-------|-----------|---------------------|--------|
| `audit_log` | Log de auditoría | 100K-1M/año |  Genérico |
| `notificaciones_workflow` | Historial de emails | 10K-100K/año |   OK |

### Configuración Email (3 tablas)

| Tabla | Propósito | Registros Esperados | Estado |
|-------|-----------|---------------------|--------|
| `cuentas_correo` | Cuentas de correo | 1-5 |   OK |
| `nit_configuracion` | NITs por cuenta | 50-200 |   OK |
| `historial_extracciones` | Log de extracciones | 1K-10K/año |   OK |

**Total**: 14 tablas activas

---

## PROBLEMAS CRÍTICOS IDENTIFICADOS

### 🔴 PROBLEMA 1: Redundancia Masiva en Tabla `facturas`

**Severidad**: CRÍTICA
**Impacto**: Inconsistencia de datos, complejidad de mantenimiento

La tabla `facturas` almacena **MÚLTIPLES DATOS REDUNDANTES** que ya existen en otras tablas:

```sql
--  REDUNDANCIA CRÍTICA
facturas:
  - aprobado_por (String)           # Ya está en workflow_aprobacion_facturas
  - fecha_aprobacion (DateTime)     # Ya está en workflow_aprobacion_facturas
  - rechazado_por (String)          # Ya está en workflow_aprobacion_facturas
  - fecha_rechazo (DateTime)        # Ya está en workflow_aprobacion_facturas
  - motivo_rechazo (String)         # Ya está en workflow_aprobacion_facturas

  - confianza_automatica (Numeric)  # Ya está en workflow (como campo calculado)
  - factura_referencia_id (BigInt)  # Ya está en workflow
  - motivo_decision (String)        # Ya está en workflow
  - fecha_procesamiento_auto (DateTime) # Ya está en workflow

  - concepto_principal (String)     # Puede calcularse de factura_items
  - concepto_hash (String)          # Puede calcularse de factura_items
  - concepto_normalizado (String)   # Puede calcularse de factura_items
  - orden_compra_numero (String)    # Puede ir en metadata
  - patron_recurrencia (String)     # Ya está en historial_pagos
```

**Consecuencias**:
- Actualización en 2+ lugares (violación DRY)
- Riesgo de inconsistencia
- Queries más lentas (tabla muy ancha)
- Índices innecesarios

**Ejemplo de inconsistencia**:
```python
# Escenario real que puede ocurrir:
factura.aprobado_por = "Juan Pérez"
factura.fecha_aprobacion = "2025-10-19"

# Pero en workflow:
workflow.aprobada_por = "María González"  #  INCONSISTENTE
workflow.fecha_aprobacion = "2025-10-18"
```

---

### 🔴 PROBLEMA 2: Violación de Tercera Forma Normal (3NF)

**Severidad**: ALTA
**Impacto**: Anomalías de actualización

La tabla `facturas` viola 3NF porque tiene **dependencias transitivas**:

```sql
facturas:
  subtotal → total_a_pagar  # total = subtotal + iva (calculable)
  iva → total_a_pagar       # total = subtotal + iva (calculable)

  proveedor_id → nit        # nit está en proveedores
  proveedor_id → razon_social # razon_social está en proveedores

  responsable_id → area     # area está en responsables
```

**Problema**: Si cambia el IVA de una factura, hay que recalcular `total_a_pagar` manualmente.

**Recomendación Senior**: Los campos calculados NO deben almacenarse, deben ser **propiedades computadas** o **vistas de base de datos**.

---

###  PROBLEMA 3: Campos Calculados Almacenados

**Severidad**: MEDIA-ALTA
**Impacto**: Mantenimiento, riesgo de desincronización

Múltiples tablas almacenan **valores calculables**:

```sql
--  MAL DISEÑO
factura_items:
  total = subtotal + total_impuestos  # CALCULABLE, no debería almacenarse

facturas:
  total_a_pagar = subtotal + iva  # CALCULABLE
  concepto_hash = MD5(concepto_normalizado)  # CALCULABLE

historial_pagos:
  rango_inferior = monto_promedio - (2 * desviacion_estandar)  # CALCULABLE
  rango_superior = monto_promedio + (2 * desviacion_estandar)  # CALCULABLE
  coeficiente_variacion = (desviacion_estandar / monto_promedio) * 100  # CALCULABLE
```

**Problema**: Si cambia `subtotal`, hay que acordarse de recalcular `total`. Alto riesgo de bugs.

**Solución Profesional**:
```python
#   CORRECTO - Computed Property
@property
def total_a_pagar(self) -> Decimal:
    return (self.subtotal or 0) + (self.iva or 0)
```

---

###  PROBLEMA 4: Duplicación entre `facturas` y `workflow_aprobacion_facturas`

**Severidad**: MEDIA
**Impacto**: Confusión, qué tabla es la "fuente de verdad"?

Ambas tablas almacenan información de aprobación/rechazo:

```sql
--  DUPLICACIÓN
facturas:
  estado (Enum)
  aprobado_por, fecha_aprobacion
  rechazado_por, fecha_rechazo, motivo_rechazo

workflow_aprobacion_facturas:
  estado (Enum - DIFERENTE!)
  aprobada_por, fecha_aprobacion, observaciones_aprobacion
  rechazada_por, fecha_rechazo, motivo_rechazo, detalle_rechazo
```

**Problemas**:
1. Dos enums diferentes para "estado"
2. Dos lugares para "aprobado_por"
3. ¿Cuál es la fuente de verdad?
4. Riesgo de desincronización

**Decisión Profesional Requerida**:
- **Opción A**: `facturas` solo tiene `estado` (simple), `workflow` tiene TODO el detalle
- **Opción B**: Eliminar campos redundantes de `facturas`, usar JOINS

---

###  PROBLEMA 5: Tabla `historial_pagos` - Duplica Información de `facturas`

**Severidad**: MEDIA
**Impacto**: Sincronización, almacenamiento

La tabla `historial_pagos` es esencialmente un **aggregate** de `facturas`:

```sql
historial_pagos:
  proveedor_id
  concepto_normalizado
  monto_promedio      # = AVG(facturas.total)
  monto_minimo        # = MIN(facturas.total)
  monto_maximo        # = MAX(facturas.total)
  desviacion_estandar # = STDDEV(facturas.total)
  pagos_detalle (JSON) # = SELECT FROM facturas
```

**Problema**: Esta tabla es un **materialized view**, pero se trata como tabla permanente.

**Solución Profesional**:
```sql
--   CORRECTO - Vista Materializada
CREATE MATERIALIZED VIEW historial_pagos_mv AS
SELECT
  proveedor_id,
  concepto_normalizado,
  AVG(total_a_pagar) as monto_promedio,
  MIN(total_a_pagar) as monto_minimo,
  MAX(total_a_pagar) as monto_maximo,
  STDDEV(total_a_pagar) as desviacion_estandar
FROM facturas
GROUP BY proveedor_id, concepto_normalizado;

-- Refrescar cada noche
REFRESH MATERIALIZED VIEW historial_pagos_mv;
```

---

###  PROBLEMA 6: Tabla `audit_log` - Demasiado Genérica

**Severidad**: BAJA-MEDIA
**Impacto**: Performance, dificultad de queries

```sql
audit_log:
  entidad (String)     # Cualquier cosa: "Factura", "Proveedor", etc.
  entidad_id (BigInt)  # ID de cualquier entidad
  accion (String)      # Cualquier acción
  detalle (JSON)       # Cualquier cosa
```

**Problemas**:
1. No hay FK real → no se puede validar integridad
2. Queries lentas (tabla MUY grande, sin particiones)
3. Difícil de consultar (tiene de todo mezclado)

**Recomendación Senior**:
- **Opción A**: Particionar por `entidad` (MySQL 8.0+)
- **Opción B**: Tablas específicas: `factura_audit`, `proveedor_audit`, etc.
- **Opción C**: Sistema externo (ElasticSearch, Kafka)

---

## VIOLACIONES DE NORMALIZACIÓN

### Primera Forma Normal (1NF):   OK

Todas las tablas cumplen 1NF:
-   Valores atómicos (no arrays)
-   Cada columna tiene tipo definido
-   No grupos repetitivos

**Excepción**: Uso de JSON en varios campos, pero es intencional y correcto para metadata.

---

### Segunda Forma Normal (2NF):   OK

Todas las tablas cumplen 2NF:
-   Todas tienen PK definida
-   No hay dependencias parciales en tablas con PK compuesta

---

### Tercera Forma Normal (3NF):  VIOLADA

**Tabla `facturas` VIOLA 3NF** por dependencias transitivas:

```sql
--  VIOLACIÓN 3NF
facturas:
  subtotal, iva → total_a_pagar
    (total puede calcularse de subtotal + iva)

  proveedor_id → nit, razon_social
    (nit y razon_social ya están en proveedores)

  factura_referencia_id → confianza_automatica
    (la confianza se calcula comparando con referencia)
```

**Tabla `factura_items` VIOLA 3NF**:

```sql
--  VIOLACIÓN 3NF
factura_items:
  subtotal, total_impuestos → total
    (total = subtotal + impuestos)

  descripcion → descripcion_normalizada, item_hash
    (son derivados de descripcion)
```

**Tabla `historial_pagos` VIOLA 3NF**:

```sql
--  VIOLACIÓN 3NF
historial_pagos:
  monto_promedio, desviacion_estandar → rango_inferior, rango_superior
    (se calculan de promedio ± 2*desv)

  desviacion_estandar, monto_promedio → coeficiente_variacion
    (CV = desv / promedio * 100)
```

---

### Forma Normal de Boyce-Codd (BCNF):  Parcialmente Violada

Algunas tablas tienen candidatos a superkey que no son PK:

```sql
facturas:
  - PK: id
  - Candidate Key: (numero_factura, proveedor_id)  # UNIQUE constraint
  - Candidate Key: cufe  # UNIQUE

  # Problema: Dos candidate keys diferentes pueden causar anomalías
```

**Recomendación**: Usar `cufe` como PK natural, `id` como surrogate opcional.

---

## REDUNDANCIA Y DUPLICACIÓN DE DATOS

### Resumen de Redundancia

| Campo | Tabla Original | Duplicado En | Tipo de Redundancia |
|-------|----------------|--------------|---------------------|
| `aprobado_por` | `workflow_aprobacion_facturas` | `facturas` | Duplicación exacta |
| `fecha_aprobacion` | `workflow_aprobacion_facturas` | `facturas` | Duplicación exacta |
| `rechazado_por` | `workflow_aprobacion_facturas` | `facturas` | Duplicación exacta |
| `fecha_rechazo` | `workflow_aprobacion_facturas` | `facturas` | Duplicación exacta |
| `motivo_rechazo` | `workflow_aprobacion_facturas` | `facturas` | Duplicación exacta |
| `total_a_pagar` | Calculable | `facturas` | Valor calculado almacenado |
| `total` | Calculable | `factura_items` | Valor calculado almacenado |
| `concepto_hash` | Calculable | `facturas`, `factura_items` | Valor calculado almacenado |
| `patron_recurrencia` | `historial_pagos` | `facturas` | Duplicación derivada |

### Impacto de Redundancia

**Almacenamiento**:
- Redundancia estimada: 20-30% del espacio de `facturas`
- Con 100K facturas: ~500MB-1GB de datos redundantes

**Performance**:
- Writes: 2-3x más lentos (actualizar múltiples tablas)
- Reads: Ligeramente más rápidos (no hacer JOINs)

**Mantenimiento**:
- Complejidad: ALTA (mantener sincronización)
- Riesgo de bugs: ALTA (olvidar actualizar un lugar)

**Trade-off**: El sistema prioriza **read performance** sobre **data consistency** y **maintainability**.

**Decisión de Arquitectura Requerida**:
- Si reads >> writes: Aceptar redundancia con triggers/eventos
- Si writes frecuentes: Eliminar redundancia, usar vistas

---

## CAMPOS CALCULADOS VS ALMACENADOS

### Análisis por Tabla

#### Tabla `facturas`

| Campo | Tipo | ¿Debería almacenarse? | Recomendación |
|-------|------|----------------------|---------------|
| `total_a_pagar` | Calculado |  NO | Computed property |
| `concepto_hash` | Calculado |  MAYBE | Generated column (MySQL 5.7+) |
| `concepto_normalizado` | Derivado |  MAYBE | Trigger o índice full-text |
| `patron_recurrencia` | Derivado |  NO | Consultar `historial_pagos` |

#### Tabla `factura_items`

| Campo | Tipo | ¿Debería almacenarse? | Recomendación |
|-------|------|----------------------|---------------|
| `total` | Calculado |  NO | Computed property |
| `descripcion_normalizada` | Derivado |  MAYBE | Generated column para índice |
| `item_hash` | Calculado |  MAYBE | Generated column |

#### Tabla `historial_pagos`

| Campo | Tipo | ¿Debería almacenarse? | Recomendación |
|-------|------|----------------------|---------------|
| `rango_inferior` | Calculado |  NO | Computed property |
| `rango_superior` | Calculado |  NO | Computed property |
| `coeficiente_variacion` | Calculado |  NO | Computed property |
| `puede_aprobar_auto` | Derivado |  NO | Business logic function |

### Recomendación Profesional: Generated Columns

```sql
--   SOLUCIÓN MODERNA: Generated Columns (MySQL 5.7+)
CREATE TABLE facturas (
  id BIGINT PRIMARY KEY,
  subtotal DECIMAL(15,2),
  iva DECIMAL(15,2),

  -- Columna generada (NO se almacena, se calcula)
  total_a_pagar DECIMAL(15,2) AS (subtotal + iva) VIRTUAL,

  -- Columna generada ALMACENADA (para índices)
  concepto_hash VARCHAR(32) AS (MD5(concepto_normalizado)) STORED,
  KEY idx_concepto_hash (concepto_hash)
);
```

**Ventajas**:
-   No se puede desincronizar (siempre correcto)
-   Código más limpio (DB maneja cálculo)
-   Puede indexarse si es STORED

---

## ANÁLISIS DE RELACIONES

### Diagrama de Relaciones (Simplificado)

```
proveedores (1) ────────────── (N) facturas
    │                             │
    │                             ├─── (N) factura_items
    │                             │
    │                             └─── (1) workflow_aprobacion_facturas
    │
    └─────────────── (N) historial_pagos

responsables (1) ────────── (N) facturas
    │
    ├─────────────── (N) asignacion_nit_responsable
    │
    └─────────────── (1) roles

cuentas_correo (1) ────────── (N) nit_configuracion
    │
    └─────────────── (N) historial_extracciones
```

### Problemas en Relaciones

#### 🔴 Problema: Relación Circular entre `facturas`

```sql
facturas:
  id (PK)
  factura_referencia_id (FK → facturas.id)  # Self-referencing
```

**Problema**: Una factura referencia a otra factura del mes anterior.

**Riesgo**: Ciclos infinitos si mal configurado.

**Recomendación**:
```sql
--   Agregar constraint para evitar ciclos
ALTER TABLE facturas
ADD CONSTRAINT chk_no_self_reference
CHECK (id != factura_referencia_id);

--   Agregar constraint de nivel
-- "La referencia debe ser más antigua"
```

####  Problema: FKs Opcionales (nullable=True)

```sql
facturas:
  proveedor_id → proveedores.id (nullable=True)  # 
  responsable_id → responsables.id (nullable=True)  # 
```

**Problema**: Una factura puede NO tener proveedor? NO tener responsable?

**Decisión de Negocio Requerida**:
- ¿Es válido tener facturas sin proveedor? → Probablemente NO
- ¿Es válido tener facturas sin responsable? → Temporalmente SÍ (hasta asignar)

**Recomendación**:
```sql
--   proveedor_id NO debería ser NULL
proveedor_id BIGINT NOT NULL

--   responsable_id puede ser NULL temporalmente
responsable_id BIGINT NULL  -- OK, se asigna después
```

####  Problema: FK sin `ON DELETE` definido

Varias FKs no tienen políticas de eliminación:

```sql
--  ¿Qué pasa si elimino un proveedor?
factura.proveedor_id → proveedores.id

-- Opciones:
-- 1. ON DELETE CASCADE: Eliminar facturas también ( PELIGROSO)
-- 2. ON DELETE RESTRICT: No permitir eliminar (  RECOMENDADO)
-- 3. ON DELETE SET NULL: Dejar huérfanas ( MAL DISEÑO)
```

**Recomendación**:
```sql
--   CORRECTO
ALTER TABLE facturas
ADD CONSTRAINT fk_factura_proveedor
FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
ON DELETE RESTRICT  -- No permitir eliminar proveedor con facturas
ON UPDATE CASCADE;  -- Actualizar si cambia PK (raro)
```

---

## RECOMENDACIONES PROFESIONALES

### Recomendación #1: Eliminar Redundancia en `facturas`

**Prioridad**: ALTA
**Esfuerzo**: Medio
**Impacto**: Alto (mejora mantenibilidad)

```sql
--  ELIMINAR de facturas:
ALTER TABLE facturas
DROP COLUMN aprobado_por,
DROP COLUMN fecha_aprobacion,
DROP COLUMN rechazado_por,
DROP COLUMN fecha_rechazo,
DROP COLUMN motivo_rechazo,
DROP COLUMN confianza_automatica,
DROP COLUMN factura_referencia_id,
DROP COLUMN motivo_decision,
DROP COLUMN fecha_procesamiento_auto;

--   MANTENER en workflow_aprobacion_facturas
-- (Fuente de verdad única)
```

**Cambio en Código**:
```python
#  ANTES
factura.aprobado_por
factura.fecha_aprobacion

#   DESPUÉS
factura.workflow.aprobada_por
factura.workflow.fecha_aprobacion
```

---

### Recomendación #2: Convertir Campos Calculados a Computed Properties

**Prioridad**: MEDIA-ALTA
**Esfuerzo**: Bajo
**Impacto**: Alto (elimina bugs)

```python
#   MODELO MEJORADO
class Factura(Base):
    __tablename__ = "facturas"

    subtotal = Column(Numeric(15, 2))
    iva = Column(Numeric(15, 2))

    #  ELIMINAR
    # total_a_pagar = Column(Numeric(15, 2))

    #   COMPUTED PROPERTY
    @property
    def total_a_pagar(self) -> Decimal:
        """Calculado dinámicamente, nunca desincronizado."""
        return (self.subtotal or Decimal(0)) + (self.iva or Decimal(0))
```

**Migración**:
```sql
-- Paso 1: Agregar columna generada
ALTER TABLE facturas
ADD COLUMN total_a_pagar_new DECIMAL(15,2) AS (subtotal + iva) VIRTUAL;

-- Paso 2: Actualizar código para usar nueva columna

-- Paso 3: Eliminar columna vieja
ALTER TABLE facturas DROP COLUMN total_a_pagar;
ALTER TABLE facturas RENAME COLUMN total_a_pagar_new TO total_a_pagar;
```

---

### Recomendación #3: Convertir `historial_pagos` a Vista Materializada

**Prioridad**: MEDIA
**Esfuerzo**: Medio
**Impacto**: Medio (mejora consistencia)

```sql
--   VISTA MATERIALIZADA
CREATE MATERIALIZED VIEW historial_pagos_mv AS
SELECT
  proveedor_id,
  concepto_normalizado,
  concepto_hash,
  COUNT(*) as pagos_analizados,
  COUNT(DISTINCT MONTH(fecha_emision)) as meses_con_pagos,
  AVG(total_a_pagar) as monto_promedio,
  MIN(total_a_pagar) as monto_minimo,
  MAX(total_a_pagar) as monto_maximo,
  STDDEV(total_a_pagar) as desviacion_estandar,
  (STDDEV(total_a_pagar) / AVG(total_a_pagar)) * 100 as coeficiente_variacion,
  AVG(total_a_pagar) - (2 * STDDEV(total_a_pagar)) as rango_inferior,
  AVG(total_a_pagar) + (2 * STDDEV(total_a_pagar)) as rango_superior,
  MAX(fecha_emision) as ultimo_pago_fecha
FROM facturas
WHERE fecha_emision >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
GROUP BY proveedor_id, concepto_normalizado;

-- Refrescar cada noche a las 2 AM
CREATE EVENT refresh_historial_pagos
ON SCHEDULE EVERY 1 DAY STARTS '2025-01-01 02:00:00'
DO REFRESH MATERIALIZED VIEW historial_pagos_mv;
```

---

### Recomendación #4: Particionar `audit_log`

**Prioridad**: BAJA-MEDIA
**Esfuerzo**: Medio
**Impacto**: Alto (performance)

```sql
--   PARTICIONADO POR RANGO (mes)
ALTER TABLE audit_log
PARTITION BY RANGE (YEAR(creado_en)*100 + MONTH(creado_en)) (
  PARTITION p202501 VALUES LESS THAN (202502),
  PARTITION p202502 VALUES LESS THAN (202503),
  PARTITION p202503 VALUES LESS THAN (202504),
  -- ...
  PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- Script de mantenimiento mensual:
-- 1. Crear partición nueva para próximo mes
-- 2. Archivar partición de hace 12 meses
```

---

### Recomendación #5: Definir Políticas de FK

**Prioridad**: ALTA
**Esfuerzo**: Bajo
**Impacto**: Alto (integridad de datos)

```sql
--   TODAS las FKs deben tener ON DELETE/UPDATE

-- Facturas
ALTER TABLE facturas
MODIFY CONSTRAINT fk_factura_proveedor
FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE facturas
MODIFY CONSTRAINT fk_factura_responsable
FOREIGN KEY (responsable_id) REFERENCES responsables(id)
ON DELETE RESTRICT ON UPDATE CASCADE;

-- Factura Items
ALTER TABLE factura_items
MODIFY CONSTRAINT fk_item_factura
FOREIGN KEY (factura_id) REFERENCES facturas(id)
ON DELETE CASCADE ON UPDATE CASCADE;  # Borrar items si se borra factura

-- Workflow
ALTER TABLE workflow_aprobacion_facturas
MODIFY CONSTRAINT fk_workflow_factura
FOREIGN KEY (factura_id) REFERENCES facturas(id)
ON DELETE RESTRICT ON UPDATE CASCADE;
```

---

### Recomendación #6: Agregar Constraints de Negocio

**Prioridad**: ALTA
**Esfuerzo**: Bajo
**Impacto**: Alto (validación a nivel DB)

```sql
--   CONSTRAINTS DE NEGOCIO

-- 1. Subtotal e IVA no pueden ser negativos
ALTER TABLE facturas
ADD CONSTRAINT chk_subtotal_positivo CHECK (subtotal >= 0),
ADD CONSTRAINT chk_iva_positivo CHECK (iva >= 0);

-- 2. Factura aprobada DEBE tener aprobado_por
-- (Si no eliminamos redundancia)
ALTER TABLE facturas
ADD CONSTRAINT chk_aprobada_con_aprobador
CHECK (
  (estado != 'aprobada' AND estado != 'aprobada_auto') OR
  (aprobado_por IS NOT NULL AND fecha_aprobacion IS NOT NULL)
);

-- 3. Factura rechazada DEBE tener motivo
ALTER TABLE facturas
ADD CONSTRAINT chk_rechazada_con_motivo
CHECK (
  estado != 'rechazada' OR
  (rechazado_por IS NOT NULL AND motivo_rechazo IS NOT NULL)
);

-- 4. Cantidad de items > 0
ALTER TABLE factura_items
ADD CONSTRAINT chk_cantidad_positiva CHECK (cantidad > 0),
ADD CONSTRAINT chk_precio_positivo CHECK (precio_unitario >= 0);

-- 5. Porcentaje de descuento válido
ALTER TABLE factura_items
ADD CONSTRAINT chk_descuento_valido
CHECK (descuento_porcentaje IS NULL OR
       (descuento_porcentaje >= 0 AND descuento_porcentaje <= 100));
```

---

## PLAN DE REFACTORIZACIÓN

### Fase 1: Quick Wins (1-2 semanas)

**Objetivo**: Mejoras rápidas sin breaking changes

1.   Agregar constraints de negocio
2.   Definir políticas ON DELETE/UPDATE en FKs
3.   Convertir campos calculados simples a `@property`
4.   Agregar índices faltantes

**Impacto**: Bajo riesgo, alta mejora en calidad

---

### Fase 2: Refactorización Media (3-4 semanas)

**Objetivo**: Eliminar redundancia, mejorar normalización

1.  Migrar campos redundantes de `facturas` a `workflow`
2.  Convertir `total_a_pagar` y `total` a Generated Columns
3.  Convertir `historial_pagos` a Materialized View
4.  Particionar `audit_log`

**Impacto**: Medio riesgo, requiere cambios en código

---

### Fase 3: Rediseño Mayor (2-3 meses)

**Objetivo**: Arquitectura óptima, nivel Fortune 500

1. 🔴 Rediseñar relación `facturas` ↔ `workflow` (Single Source of Truth)
2. 🔴 Implementar Event Sourcing para auditoría
3. 🔴 Separar tablas de lectura (CQRS pattern)
4. 🔴 Implementar sharding por año/proveedor

**Impacto**: Alto riesgo, requiere rediseño completo

---

## MODELO PROPUESTO (MEJORADO)

### Tabla `facturas` - Versión Mejorada

```sql
CREATE TABLE facturas (
  -- Identificación
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  cufe VARCHAR(100) UNIQUE NOT NULL,  -- Debería ser PK natural
  numero_factura VARCHAR(50) NOT NULL,

  -- Fechas
  fecha_emision DATE NOT NULL,
  fecha_vencimiento DATE NULL,

  -- Relaciones (OBLIGATORIAS)
  proveedor_id BIGINT NOT NULL,
  responsable_id BIGINT NULL,  -- NULL temporal hasta asignar

  -- Montos (sin campos calculados)
  subtotal DECIMAL(15,2) NOT NULL CHECK (subtotal >= 0),
  iva DECIMAL(15,2) NOT NULL CHECK (iva >= 0),

  -- Campo calculado (Generated Column)
  total_a_pagar DECIMAL(15,2) AS (subtotal + iva) STORED,

  -- Estado (SIMPLE)
  estado ENUM('pendiente', 'aprobada', 'rechazada', 'pagada') NOT NULL DEFAULT 'pendiente',

  -- Tipo de factura
  tipo_factura VARCHAR(20) NOT NULL DEFAULT 'COMPRA',

  -- Metadata mínima
  concepto_principal VARCHAR(500) NULL,

  -- Auditoría
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  -- FKs con políticas
  FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  FOREIGN KEY (responsable_id) REFERENCES responsables(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  -- Índices
  UNIQUE KEY uix_num_prov (numero_factura, proveedor_id),
  INDEX idx_fecha_estado (fecha_emision, estado),
  INDEX idx_proveedor_fecha (proveedor_id, fecha_emision),
  INDEX idx_responsable_estado (responsable_id, estado)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Cambios**:
-  Eliminados 10+ campos redundantes
-   `total_a_pagar` como Generated Column
-   Constraints de negocio
-   FKs con políticas
-   Índices optimizados

---

### Tabla `workflow_aprobacion_facturas` - Versión Mejorada

```sql
CREATE TABLE workflow_aprobacion_facturas (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  factura_id BIGINT NOT NULL UNIQUE,  -- 1:1 con facturas

  -- Estado del workflow (DETALLADO)
  estado ENUM(
    'recibida', 'en_analisis', 'aprobada_auto',
    'pendiente_revision', 'en_revision', 'aprobada_manual',
    'rechazada', 'observada', 'enviada_contabilidad', 'procesada'
  ) NOT NULL DEFAULT 'recibida',
  fecha_cambio_estado DATETIME NOT NULL,

  -- Asignación
  responsable_id BIGINT NULL,
  fecha_asignacion DATETIME NULL,

  -- Análisis automático
  factura_mes_anterior_id BIGINT NULL,
  porcentaje_similitud DECIMAL(5,2) NULL,
  diferencias_detectadas JSON NULL,

  -- Aprobación (FUENTE DE VERDAD)
  tipo_aprobacion ENUM('automatica', 'manual', 'masiva', 'forzada') NULL,
  aprobada BOOLEAN NOT NULL DEFAULT FALSE,
  aprobada_por VARCHAR(255) NULL,
  fecha_aprobacion DATETIME NULL,
  observaciones_aprobacion TEXT NULL,

  -- Rechazo (FUENTE DE VERDAD)
  rechazada BOOLEAN NOT NULL DEFAULT FALSE,
  rechazada_por VARCHAR(255) NULL,
  fecha_rechazo DATETIME NULL,
  motivo_rechazo ENUM(...) NULL,
  detalle_rechazo TEXT NULL,

  -- Tiempos (para métricas)
  tiempo_en_analisis BIGINT NULL,
  tiempo_en_revision BIGINT NULL,

  -- Auditoría
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  -- FKs
  FOREIGN KEY (factura_id) REFERENCES facturas(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  FOREIGN KEY (responsable_id) REFERENCES responsables(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  FOREIGN KEY (factura_mes_anterior_id) REFERENCES facturas(id)
    ON DELETE SET NULL ON UPDATE CASCADE,

  -- Índices
  INDEX idx_estado_responsable (estado, responsable_id),
  INDEX idx_estado_fecha (estado, fecha_cambio_estado)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Filosofía**: `workflow` es la fuente de verdad para aprobación/rechazo, `facturas.estado` es solo un snapshot simple.

---

## CONCLUSIONES Y CALIFICACIÓN FINAL

### Calificación por Aspecto

| Aspecto | Calificación | Comentario |
|---------|--------------|------------|
| **Normalización** | 6/10 | Viola 3NF en varias tablas |
| **Redundancia** | 5/10 | Alta redundancia entre `facturas` y `workflow` |
| **Integridad Referencial** | 7/10 | FKs OK, faltan políticas ON DELETE |
| **Constraints de Negocio** | 6/10 | Algunos constraints, faltan muchos |
| **Índices** | 8/10 | Buenos índices compuestos |
| **Campos Calculados** | 4/10 | Muchos almacenados innecesariamente |
| **Diseño de Workflow** | 9/10 | Excelente diseño de workflow |
| **Auditoría** | 8/10 | Completa pero tabla muy genérica |
| **Escalabilidad** | 7/10 | OK para 100K facturas/año |
| **Mantenibilidad** | 6/10 | Complejidad por redundancia |

**Calificación Global**: **7.5/10** - Buena pero con mejoras críticas necesarias

---

### Fortalezas del Diseño Actual

  **Workflow robusto**: El diseño de `workflow_aprobacion_facturas` es de nivel enterprise.

  **Auditoría completa**: Sistema de alertas y notificaciones bien pensado.

  **Campos de metadata**: Buen uso de JSON para datos flexibles.

  **Relaciones bien definidas**: La mayoría de FKs están correctas.

  **Índices compuestos**: Buenos índices para queries frecuentes.

---

### Debilidades Críticas

🔴 **Redundancia masiva**: Duplicación de datos entre `facturas` y `workflow`.

🔴 **Violación 3NF**: Campos calculados almacenados innecesariamente.

🔴 **Complejidad de mantenimiento**: Actualizar múltiples tablas para un cambio.

🔴 **Riesgo de inconsistencia**: Sin triggers, puede desincronizarse.

🔴 **Falta constraints**: Validaciones de negocio faltan a nivel DB.

---

### Recomendación Final

**Como equipo senior**, recomendamos ejecutar **Fase 1 (Quick Wins) INMEDIATAMENTE** para mejorar la calidad sin riesgo.

**Fase 2 (Refactorización Media)** debe planificarse para Q1 2026.

**Fase 3 (Rediseño Mayor)** puede postergarse hasta que el sistema escale a >500K facturas/año.

**Prioridad #1**: Eliminar redundancia entre `facturas` y `workflow`. Esto es el riesgo más grande actualmente.

---

**Documento preparado por**: Equipo de Desarrollo Senior AFE
**Fecha**: Octubre 19, 2025
**Próxima revisión**: Enero 2026 (post-implementación Fase 1)

---

** Objetivo**: Base de datos limpia, sin ambigüedad, sin duplicación, mantenible, escalable, nivel enterprise.

**¿Es coherente con lo que estamos desarrollando?**
**Respuesta**: SÍ, es coherente, pero requiere refactorización para alcanzar nivel profesional Fortune 500.
