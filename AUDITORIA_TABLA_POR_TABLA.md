# 🔍 AUDITORÍA TABLA POR TABLA - SISTEMA AFE

**Fecha**: 2025-11-25
**Metodología**: Búsqueda exhaustiva de cada campo en código fuente
**Criterio**: Un campo se considera "EN USO" si aparece en queries, asignaciones o lectura de datos

---

# TABLA 1: `facturas` (29 campos)

## ✅ CAMPOS EN USO ACTIVO (VERIFICADO)

| # | Campo | Tipo | Uso Confirmado | Archivos |
|---|-------|------|----------------|----------|
| 1 | `id` | BIGINT | ✅ PK, FK en múltiples tablas | Todos |
| 2 | `numero_factura` | VARCHAR(50) | ✅ Identificador, queries, filtros | 20+ archivos |
| 3 | `fecha_emision` | DATE | ✅ Filtros de período, ordenamiento | 20+ archivos |
| 4 | `proveedor_id` | BIGINT | ✅ FK crítica, queries, joins | Todos |
| 5 | `subtotal` | DECIMAL(15,2) | ✅ Cálculos de total_calculado | 20+ archivos |
| 6 | `iva` | DECIMAL(15,2) | ✅ Cálculos de total_calculado | workflow, crud |
| 7 | `estado` | ENUM | ✅ CRÍTICO - Control workflow | Todos |
| 8 | `fecha_vencimiento` | DATE | ✅ Reportes, alertas | accounting, export |
| 9 | `cufe` | VARCHAR(100) | ✅ UNIQUE, validación duplicados | facturas router |
| 10 | `total_a_pagar` | DECIMAL(15,2) | ✅ **FUENTE DE VERDAD pagos** | 20+ archivos |
| 11 | `responsable_id` | BIGINT | ✅ FK crítica, asignación | Todos |
| 12 | `creado_en` | DATETIME | ✅ Auditoría, ordenamiento | Todos |
| 13 | `actualizado_en` | DATETIME | ✅ Auditoría, sync | Todos |
| 25 | `accion_por` | VARCHAR(255) | ✅ **Single source of truth** aprobación | workflow, crud |
| 26 | `estado_asignacion` | ENUM | ✅ PHASE 3 tracking | workflow |
| 27 | `retenciones` | DECIMAL(15,2) | ✅ Impuestos retenidos | Añadido 2025-10-23 |
| 28 | `empresa_id` | BIGINT | ✅ FK a empresas | Multi-empresa |
| 29 | `sede_id` | BIGINT | ✅ FK a sedes | Multi-sede |

**Total campos activos confirmados**: 18 campos

---

## ⚠️ CAMPOS DEPRECATED (EN USO pero marcados para migración)

| # | Campo | Tipo | Estado | Plan |
|---|-------|------|--------|------|
| 14 | `confianza_automatica` | DECIMAL(3,2) | ⚠️ USADO en flujo_automatizacion línea 455 | Migrar a workflow |
| 15 | `factura_referencia_id` | BIGINT | ⚠️ USADO en flujo_automatizacion línea 457, 474 | Migrar a workflow |
| 16 | `motivo_decision` | VARCHAR(500) | ⚠️ USADO en flujo_automatizacion línea 456, 473 | Migrar a workflow |
| 17 | `fecha_procesamiento_auto` | DATETIME | ⚠️ USADO en flujo_automatizacion línea 458, 475 | Migrar a workflow |
| 18 | `concepto_principal` | VARCHAR(500) | ⚠️ USADO en flujo_automatizacion línea 378 | Migrar a factura_items |
| 19 | `concepto_hash` | VARCHAR(32) | ⚠️ USADO en flujo_automatizacion línea 379, 384 | Migrar a factura_items |
| 20 | `concepto_normalizado` | VARCHAR(500) | ⚠️ USADO en flujo_automatizacion línea 378 | Migrar a factura_items |
| 21 | `orden_compra_numero` | VARCHAR(50) | ⚠️ USADO en workflow_automatico línea 557-562 | Migrar a factura_items |
| 22 | `patron_recurrencia` | VARCHAR(20) | ⚠️ USADO en análisis de historial | Migrar a factura_items |
| 23 | `tipo_factura` | VARCHAR(20) | ⚠️ USADO con default 'COMPRA' | Migrar a factura_items |

**Total campos deprecated pero EN USO**: 10 campos

**⚠️ CRÍTICO**: Estos campos NO pueden eliminarse sin refactorizar primero `flujo_automatizacion_facturas.py` y `workflow_automatico.py`

---

## ✅ CAMPO ESPECIAL (COLUMNA VIRTUAL)

| # | Campo | Tipo | Estado | Explicación |
|---|-------|------|--------|-------------|
| 24 | `total_calculado_validacion` | DECIMAL(15,2) | ✅ COLUMNA VIRTUAL | Generada automáticamente = `subtotal + iva - retenciones` |

**Explicación**: Esta es una **GENERATED COLUMN** de MySQL (migración `6060d9a9969f_fase2_5`). Se calcula automáticamente por la BD. NO se escribe desde código Python. Se usa en constraint para validar coherencia:
```sql
CHECK (ABS(total_a_pagar - total_calculado_validacion) <= 0.01)
```

**Decisión**: **MANTENER** - Es parte de la integridad de datos a nivel BD

---

## 📊 RESUMEN TABLA `facturas`

| Categoría | Cantidad |
|-----------|----------|
| ✅ Campos activos | 18 |
| ⚠️ Campos deprecated (en uso) | 10 |
| ❓ Campos a investigar | 1 |
| ❌ Campos sin uso | 0 |
| **TOTAL** | **29** |

**Conclusión**: Todos los campos de `facturas` están en uso. Los 10 deprecated requieren refactoring antes de eliminar.

---

# TABLA 2: `factura_items` (20 campos)

## ✅ CAMPOS EN USO ACTIVO (VERIFICADO)

| # | Campo | Tipo | Uso Confirmado | Archivos |
|---|-------|------|----------------|----------|
| 1 | `id` | BIGINT | ✅ PK | Todos |
| 2 | `factura_id` | BIGINT | ✅ FK crítica (CASCADE DELETE) | Todos |
| 3 | `numero_linea` | INTEGER | ✅ Ordenamiento de items | comparador_items |
| 4 | `descripcion` | VARCHAR(2000) | ✅ Texto del item | Todos |
| 5 | `codigo_producto` | VARCHAR(100) | ✅ Identificación de productos | comparador, matching |
| 7 | `cantidad` | DECIMAL(15,4) | ✅ Cantidad de unidades | cálculos |
| 8 | `unidad_medida` | VARCHAR(50) | ✅ Tipo de unidad | export |
| 9 | `precio_unitario` | DECIMAL(15,4) | ✅ Precio por unidad | cálculos |
| 10 | `total_impuestos` | DECIMAL(15,2) | ✅ Impuestos del item | cálculos |
| 13 | `descripcion_normalizada` | VARCHAR(500) | ✅ Matching y comparación | comparador_items |
| 14 | `item_hash` | VARCHAR(32) | ✅ Hash MD5 para búsqueda rápida | comparador_items |
| 15 | `categoria` | VARCHAR(100) | ✅ Clasificación del item | análisis |
| 16 | `es_recurrente` | DECIMAL(1,0) | ✅ Flag de recurrencia mensual | análisis |
| 18 | `creado_en` | DATETIME | ✅ Auditoría | Todos |
| 19 | `subtotal` | DECIMAL(15,2) | ⚠️ **DEPRECATED** pero en uso | propiedad subtotal_calculado |
| 20 | `total` | DECIMAL(15,2) | ⚠️ **DEPRECATED** pero en uso | propiedad total_calculado |

**Total campos activos**: 16 campos

---

## ⚠️ CAMPO EN USO (Lectura Interna)

| # | Campo | Tipo | Estado | Explicación |
|---|-------|------|--------|-------------|
| 12 | `descuento_valor` | DECIMAL(15,2) | ⚠️ **SOLO LECTURA INTERNA** | Usado SOLO en propiedad `subtotal_calculado` línea 261 |

**Explicación**: Este campo se lee en la propiedad calculada:
```python
descuento = self.descuento_valor or Decimal('0')
return (cantidad * precio) - descuento
```

Pero **NUNCA** se lee desde servicios/routers/CRUD externos. Solo el modelo lo usa internamente.

**Decisión**: ⚠️ **EVALUAR** - Si subtotal_calculado no se usa, este campo tampoco sirve

---

## ❌ CAMPOS SIN USO (CONFIRMADO - ELIMINAR)

| # | Campo | Tipo | Estado | Archivos | Decisión |
|---|-------|------|--------|----------|----------|
| 6 | `codigo_estandar` | VARCHAR(100) | ❌ **CERO referencias** | grep: 0 resultados | ✅ ELIMINAR |
| 11 | `descuento_porcentaje` | DECIMAL(5,2) | ❌ **CERO referencias** | grep: 0 resultados | ✅ ELIMINAR |
| 17 | `notas` | VARCHAR(1000) | ❌ **Campo de otra tabla** | notas de `nit_configuracion` | ✅ ELIMINAR |

**Confirmación NOTAS**: El grep encontró `notas` pero es de la tabla `nit_configuracion` (línea 206 en email_config.py), NO de `factura_items`.

**Total campos a eliminar INMEDIATAMENTE**: 3 campos (`codigo_estandar`, `descuento_porcentaje`, `notas`)

---

## 📊 RESUMEN TABLA `factura_items`

| Categoría | Cantidad |
|-----------|----------|
| ✅ Campos activos | 16 |
| ⚠️ Uso interno solamente | 1 (`descuento_valor`) |
| ✅ **ELIMINADOS** (2025-11-25) | 3 |
| **TOTAL** | **17** |

**✅ COMPLETADO** (2025-11-25): Eliminados 3 campos (`codigo_estandar`, `descuento_porcentaje`, `notas`)
- Migración: `2d665e89c06b_remove_unused_fields_from_factura_items`
- Estado: Ejecutada exitosamente

**Acción futura**: Evaluar si `descuento_valor` puede eliminarse junto con revisión de `subtotal_calculado`

---

# TABLA 3: `proveedores` (Pendiente)

## 🔄 Estado: Pendiente análisis detallado

---

# TABLA 4: `responsables` (Pendiente)

## 🔄 Estado: Pendiente análisis detallado

---

# TABLA 5: `roles` (Pendiente)

## ✅ Estado: **TABLA EN USO ACTIVO** (confirmado)

- ✅ FK activa desde `responsables.role_id`
- ✅ CRUD operations activo
- ✅ Queries en `accounting_notification_service.py`
- ✅ Catálogo de roles: admin, responsable, contador, viewer

**Decisión**: **MANTENER** - NO eliminar

---

# TABLA 6: `pagos_facturas` (ELIMINADA ✅)

## ✅ Estado: **ELIMINADA COMPLETAMENTE** (2025-11-25)

**Razón de eliminación**: Código creado hace menos de una semana (2025-11-20). Responsabilidad de pagos es externa (tesorería).

**Archivos eliminados**:
- ❌ `app/models/pago_factura.py` - Modelo eliminado
- ❌ `app/schemas/pago.py` - Schemas eliminados
- ❌ `app/api/v1/routers/accounting.py` - 3 endpoints eliminados:
  - `/facturas/pendientes` (GET)
  - `/historial-pagos` (GET)
  - `/facturas/{id}/marcar-pagada` (POST)
- ❌ `tests/test_payment_system.py` - Tests eliminados
- ❌ `tests/conftest.py` - Fixture `limpiar_pagos_test` eliminada
- ❌ `alembic/versions/2025_11_20_add_payment_system.py` - Migración eliminada

**Código limpiado**:
- ❌ `app/models/factura.py` - Eliminada relación `pagos` y propiedades:
  - `total_pagado`
  - `pendiente_pagar`
  - `esta_completamente_pagada`

**Migración de eliminación**:
- `e81dd7999fd0_remove_pagos_facturas_table.py`
- Estado: ✅ Ejecutada exitosamente
- Tabla NO existía en BD (migración original nunca se ejecutó)

---

# TABLA 7-21: Pendientes

Tablas restantes para auditoría:
- asignacion_nit_responsable
- audit_log
- auditoria_login
- workflow_aprobacion_facturas
- historial_pagos
- notificaciones_workflow
- cuentas_correo
- nit_configuracion
- historial_extracciones
- alertas_aprobacion_automatica
- empresas
- sedes
- mapeo_correos_empresas
- responsables_empresa
- alembic_version (sistema, no tocar)

---

## PRÓXIMOS PASOS

1. ✅ Tabla `facturas` - COMPLETADA
2. ⏳ Investigar campo `total_calculado_validacion`
3. ⏳ Auditar tabla `factura_items` completa
4. ⏳ Auditar tabla `historial_pagos` completa
5. ⏳ Continuar con tablas restantes

---

**Documento en progreso - Se actualizará tabla por tabla**
