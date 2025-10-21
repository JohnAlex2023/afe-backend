# PLAN DE REFACTORIZACIÓN DB - FASE 1 (Quick Wins)

**Objetivo**: Llevar la base de datos a nivel 100% profesional
**Enfoque**: Cambios de bajo riesgo, alto impacto
**Tiempo estimado**: 1-2 semanas
**Impacto en código**: Mínimo (sin breaking changes)

---

## ESTRATEGIA PROFESIONAL

Como equipo senior, vamos a ser **incremental y seguro**:

1.   **NO eliminar campos** todavía (alto riesgo de breaking changes)
2.   **Agregar constraints** y validaciones (mejora calidad)
3.   **Definir políticas FK** (mejora integridad)
4.   **Convertir campos calculados** a properties (código Python)
5.   **Deprecar campos** en modelos (documentar para futuro)

**Filosofía**: Mejorar sin romper. Los cambios grandes (eliminar redundancia) van en Fase 2.

---

## CAMBIOS A IMPLEMENTAR - FASE 1

### 1. Constraints de Negocio (DB Level)

**Riesgo**: BAJO
**Impacto**: ALTO (previene datos inválidos)
**Breaking Changes**: NO

```sql
-- Validar montos positivos
ALTER TABLE facturas
ADD CONSTRAINT chk_facturas_subtotal_positivo CHECK (subtotal >= 0),
ADD CONSTRAINT chk_facturas_iva_positivo CHECK (iva >= 0);

-- Validar cantidades positivas en items
ALTER TABLE factura_items
ADD CONSTRAINT chk_items_cantidad_positiva CHECK (cantidad > 0),
ADD CONSTRAINT chk_items_precio_positivo CHECK (precio_unitario >= 0),
ADD CONSTRAINT chk_items_subtotal_positivo CHECK (subtotal >= 0);

-- Validar porcentaje de descuento
ALTER TABLE factura_items
ADD CONSTRAINT chk_items_descuento_valido
CHECK (descuento_porcentaje IS NULL OR
       (descuento_porcentaje >= 0 AND descuento_porcentaje <= 100));

-- Validar estado aprobado tiene aprobador
ALTER TABLE facturas
ADD CONSTRAINT chk_facturas_aprobada_con_aprobador
CHECK (
  (estado NOT IN ('aprobada', 'aprobada_auto')) OR
  (aprobado_por IS NOT NULL AND fecha_aprobacion IS NOT NULL)
);

-- Validar estado rechazado tiene motivo
ALTER TABLE facturas
ADD CONSTRAINT chk_facturas_rechazada_con_motivo
CHECK (
  estado != 'rechazada' OR
  (rechazado_por IS NOT NULL AND motivo_rechazo IS NOT NULL)
);
```

### 2. Políticas ON DELETE/UPDATE en FKs

**Riesgo**: BAJO
**Impacto**: ALTO (previene inconsistencia)
**Breaking Changes**: NO

```sql
-- FACTURAS → PROVEEDORES
ALTER TABLE facturas
DROP FOREIGN KEY facturas_ibfk_1,  -- Nombre auto-generado por MySQL
ADD CONSTRAINT fk_facturas_proveedor
FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
ON DELETE RESTRICT  -- No permitir eliminar proveedor con facturas
ON UPDATE CASCADE;

-- FACTURAS → RESPONSABLES
ALTER TABLE facturas
DROP FOREIGN KEY facturas_ibfk_2,
ADD CONSTRAINT fk_facturas_responsable
FOREIGN KEY (responsable_id) REFERENCES responsables(id)
ON DELETE RESTRICT
ON UPDATE CASCADE;

-- FACTURA_ITEMS → FACTURAS
ALTER TABLE factura_items
DROP FOREIGN KEY factura_items_ibfk_1,
ADD CONSTRAINT fk_items_factura
FOREIGN KEY (factura_id) REFERENCES facturas(id)
ON DELETE CASCADE  -- Eliminar items si se elimina factura
ON UPDATE CASCADE;

-- WORKFLOW → FACTURAS
ALTER TABLE workflow_aprobacion_facturas
DROP FOREIGN KEY workflow_aprobacion_facturas_ibfk_1,
ADD CONSTRAINT fk_workflow_factura
FOREIGN KEY (factura_id) REFERENCES facturas(id)
ON DELETE RESTRICT  -- No eliminar factura con workflow
ON UPDATE CASCADE;

-- WORKFLOW → RESPONSABLES
ALTER TABLE workflow_aprobacion_facturas
DROP FOREIGN KEY workflow_aprobacion_facturas_ibfk_2,
ADD CONSTRAINT fk_workflow_responsable
FOREIGN KEY (responsable_id) REFERENCES responsables(id)
ON DELETE RESTRICT
ON UPDATE CASCADE;

-- ASIGNACION_NIT → RESPONSABLES
ALTER TABLE asignacion_nit_responsable
DROP FOREIGN KEY asignacion_nit_responsable_ibfk_1,
ADD CONSTRAINT fk_asignacion_responsable
FOREIGN KEY (responsable_id) REFERENCES responsables(id)
ON DELETE RESTRICT
ON UPDATE CASCADE;

-- HISTORIAL_PAGOS → PROVEEDORES
ALTER TABLE historial_pagos
DROP FOREIGN KEY historial_pagos_ibfk_1,
ADD CONSTRAINT fk_historial_proveedor
FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
ON DELETE CASCADE  -- Eliminar historial si se elimina proveedor
ON UPDATE CASCADE;
```

### 3. Computed Properties en Modelos Python

**Riesgo**: BAJO
**Impacto**: ALTO (elimina riesgo de desincronización)
**Breaking Changes**: NO (backward compatible)

```python
# app/models/factura.py

class Factura(Base):
    __tablename__ = "facturas"

    # Campos base (se mantienen)
    subtotal = Column(Numeric(15, 2))
    iva = Column(Numeric(15, 2))
    total_a_pagar = Column(Numeric(15, 2))  #  DEPRECATED, usar property

    #   COMPUTED PROPERTY (siempre correcto)
    @property
    def total_calculado(self) -> Decimal:
        """
        Total calculado dinámicamente (siempre correcto).

        Usar este en lugar de total_a_pagar en código nuevo.
        total_a_pagar se mantiene por compatibilidad pero será eliminado en v2.0
        """
        return (self.subtotal or Decimal(0)) + (self.iva or Decimal(0))

    # Validación automática (antes de guardar)
    @validates('total_a_pagar')
    def validate_total_a_pagar(self, key, value):
        """
        Valida que total_a_pagar sea igual a subtotal + iva.
        Si es diferente, lanza warning o corrige automáticamente.
        """
        if value is not None:
            expected = self.total_calculado
            if value != expected:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Factura {self.id}: total_a_pagar ({value}) != "
                    f"subtotal+iva ({expected}). Auto-corrigiendo."
                )
                return expected
        return value
```

```python
# app/models/factura_item.py

class FacturaItem(Base):
    __tablename__ = "factura_items"

    subtotal = Column(Numeric(15, 2))
    total_impuestos = Column(Numeric(15, 2))
    total = Column(Numeric(15, 2))  #  DEPRECATED

    @property
    def total_calculado(self) -> Decimal:
        """Total calculado dinámicamente."""
        return (self.subtotal or Decimal(0)) + (self.total_impuestos or Decimal(0))

    @validates('total')
    def validate_total(self, key, value):
        """Auto-corrige total si está desincronizado."""
        if value is not None:
            expected = self.total_calculado
            if value != expected:
                return expected
        return value
```

### 4. Deprecation Warnings en Campos Redundantes

**Riesgo**: BAJO
**Impacto**: MEDIO (documenta para refactorización futura)
**Breaking Changes**: NO

```python
# app/models/factura.py

class Factura(Base):
    __tablename__ = "facturas"

    #  DEPRECATED FIELDS - Usar workflow en su lugar
    # Estos campos serán eliminados en v2.0 (Fase 2)
    aprobado_por = Column(
        String(100),
        nullable=True,
        comment=" DEPRECATED: Usar workflow.aprobada_por. Eliminar en v2.0"
    )
    fecha_aprobacion = Column(
        DateTime(timezone=True),
        nullable=True,
        comment=" DEPRECATED: Usar workflow.fecha_aprobacion. Eliminar en v2.0"
    )
    rechazado_por = Column(
        String(100),
        nullable=True,
        comment=" DEPRECATED: Usar workflow.rechazada_por. Eliminar en v2.0"
    )
    # ... otros campos deprecated

    #   Helper method para acceder a datos del workflow
    def get_aprobado_por(self) -> Optional[str]:
        """
        Obtiene quién aprobó la factura.

        Primero intenta desde workflow (fuente de verdad),
        fallback a campo deprecated.
        """
        if hasattr(self, 'workflow') and self.workflow:
            return self.workflow.aprobada_por
        return self.aprobado_por  # Fallback deprecated

    def get_fecha_aprobacion(self) -> Optional[datetime]:
        """Obtiene fecha de aprobación desde workflow."""
        if hasattr(self, 'workflow') and self.workflow:
            return self.workflow.fecha_aprobacion
        return self.fecha_aprobacion  # Fallback
```

### 5. Índices Adicionales para Performance

**Riesgo**: BAJO
**Impacto**: MEDIO (mejora queries)
**Breaking Changes**: NO

```sql
-- Facturas: búsqueda por fecha y estado (común en dashboard)
CREATE INDEX idx_facturas_fecha_estado
ON facturas(fecha_emision DESC, estado);

-- Facturas: búsqueda por proveedor y fecha (reportes)
CREATE INDEX idx_facturas_proveedor_fecha
ON facturas(proveedor_id, fecha_emision DESC);

-- Facturas: búsqueda por responsable y estado (workflow)
CREATE INDEX idx_facturas_responsable_estado
ON facturas(responsable_id, estado)
WHERE responsable_id IS NOT NULL;

-- Workflow: búsqueda de pendientes por responsable
CREATE INDEX idx_workflow_pendientes
ON workflow_aprobacion_facturas(responsable_id, estado, fecha_cambio_estado)
WHERE estado IN ('pendiente_revision', 'en_revision');

-- Items: búsqueda por código de producto
CREATE INDEX idx_items_codigo_producto
ON factura_items(codigo_producto)
WHERE codigo_producto IS NOT NULL;
```

---

## MIGRACIONES ALEMBIC

Voy a crear 3 migraciones separadas:

1. `add_business_constraints.py` - Constraints de negocio
2. `update_fk_policies.py` - Políticas ON DELETE/UPDATE
3. `add_performance_indexes.py` - Índices adicionales

---

## TESTING PLAN

### Pre-Migration Tests

```bash
# 1. Backup de base de datos
mysqldump bd_afe > backup_pre_fase1_$(date +%Y%m%d).sql

# 2. Contar registros
SELECT COUNT(*) FROM facturas;
SELECT COUNT(*) FROM factura_items;
SELECT COUNT(*) FROM workflow_aprobacion_facturas;

# 3. Identificar datos que violarían constraints
-- Facturas con subtotal negativo
SELECT COUNT(*) FROM facturas WHERE subtotal < 0;

-- Facturas aprobadas sin aprobador
SELECT COUNT(*) FROM facturas
WHERE estado IN ('aprobada', 'aprobada_auto')
AND (aprobado_por IS NULL OR fecha_aprobacion IS NULL);

-- Items con cantidad negativa
SELECT COUNT(*) FROM factura_items WHERE cantidad <= 0;
```

### Post-Migration Tests

```bash
# 1. Verificar constraints existen
SHOW CREATE TABLE facturas;
SHOW CREATE TABLE factura_items;

# 2. Test de intento de violación
-- Debería fallar:
INSERT INTO facturas (subtotal, iva) VALUES (-100, 50);

# 3. Verificar FKs tienen políticas
SELECT
  TABLE_NAME,
  CONSTRAINT_NAME,
  REFERENCED_TABLE_NAME,
  UPDATE_RULE,
  DELETE_RULE
FROM information_schema.REFERENTIAL_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'bd_afe';

# 4. Verificar índices existen
SHOW INDEX FROM facturas;
SHOW INDEX FROM workflow_aprobacion_facturas;
```

---

## ROLLBACK PLAN

Si algo sale mal:

```bash
# 1. Restaurar backup
mysql bd_afe < backup_pre_fase1_YYYYMMDD.sql

# 2. O revertir migraciones Alembic
alembic downgrade -1
alembic downgrade -1
alembic downgrade -1

# 3. Verificar estado
alembic current
```

---

## IMPACTO EN CÓDIGO EXISTENTE

### Código que NO requiere cambios:

  Lecturas de `total_a_pagar`, `aprobado_por`, etc. → Siguen funcionando
  Escrituras que ya calculan correctamente → Siguen funcionando
  Queries existentes → Siguen funcionando

### Código que OPCIONALMENTE puede mejorarse:

 Usar `factura.total_calculado` en lugar de `factura.total_a_pagar`
 Usar `factura.get_aprobado_por()` en lugar de acceso directo
 Nuevos endpoints pueden empezar a usar workflow directamente

### Código que DEBE cambiarse (muy poco):

🔴 Código que intenta insertar subtotal negativo → Ya debería validar
🔴 Código que aprueba sin asignar aprobador → Ya debería validar

---

## CRONOGRAMA

### Día 1-2: Análisis y Preparación
- [x] Analizar impacto de cambios
- [ ] Crear migraciones Alembic
- [ ] Backup de producción
- [ ] Testing en desarrollo

### Día 3: Ejecución en Desarrollo
- [ ] Ejecutar migraciones en dev
- [ ] Verificar constraints
- [ ] Verificar FKs
- [ ] Testing manual

### Día 4-5: Testing y Validación
- [ ] Tests unitarios
- [ ] Tests de integración
- [ ] Performance testing
- [ ] Code review

### Día 6: Staging
- [ ] Deploy a staging
- [ ] Testing completo
- [ ] Validación con QA

### Día 7-10: Producción
- [ ] Backup de producción
- [ ] Deploy en ventana de mantenimiento
- [ ] Monitoring 24h
- [ ] Validación post-deploy

---

## MÉTRICAS DE ÉXITO

| Métrica | Objetivo |
|---------|----------|
| Constraints agregados | 10+ |
| FKs con políticas | 100% |
| Índices adicionales | 5+ |
| Tests pasando | 100% |
| Downtime | 0 minutos |
| Bugs introducidos | 0 |
| Performance | Igual o mejor |

---

## FASE 2 (FUTURO)

Una vez Fase 1 esté en producción y estable (1-2 meses):

- Eliminar campos redundantes de `facturas`
- Convertir `total_a_pagar` a Generated Column
- Convertir `historial_pagos` a Materialized View
- Refactorizar código para usar workflow como fuente de verdad

---

**Este plan es conservador, profesional, y de bajo riesgo.**
**Mejora la calidad sin romper el sistema.**

**Próximo paso**: Crear las 3 migraciones Alembic.
