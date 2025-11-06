-- ============================================================================
-- SCRIPT: Convertir subtotal y total a GENERATED COLUMNS
-- ============================================================================
-- Este script corrige el problema donde las columnas subtotal y total
-- en factura_items no fueron convertidas a GENERATED COLUMNS correctamente.
--
-- IMPORTANTE: Este script es idempotente - puede ejecutarse múltiples veces.
-- ============================================================================

USE bd_afe;

-- Paso 1: Verificar si las columnas ya son GENERATED
SELECT
    COLUMN_NAME,
    GENERATION_EXPRESSION,
    EXTRA
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'bd_afe'
  AND TABLE_NAME = 'factura_items'
  AND COLUMN_NAME IN ('subtotal', 'total');

-- Si GENERATION_EXPRESSION es NULL, entonces NO son GENERATED y hay que convertirlas

-- ============================================================================
-- PASO 2: Convertir subtotal a GENERATED STORED
-- ============================================================================

-- 2.1: Renombrar columna actual a _old
ALTER TABLE factura_items
CHANGE COLUMN subtotal subtotal_old DECIMAL(15,2);

-- 2.2: Crear nueva columna como GENERATED
ALTER TABLE factura_items
ADD COLUMN subtotal DECIMAL(15,2)
GENERATED ALWAYS AS (
    (cantidad * precio_unitario) - COALESCE(descuento_valor, 0)
) STORED
COMMENT 'Subtotal calculado: cantidad × precio - descuento';

-- 2.3: Eliminar columna vieja
ALTER TABLE factura_items
DROP COLUMN subtotal_old;

-- ============================================================================
-- PASO 3: Convertir total a GENERATED STORED
-- ============================================================================

-- 3.1: Renombrar columna actual a _old
ALTER TABLE factura_items
CHANGE COLUMN total total_old DECIMAL(15,2);

-- 3.2: Crear nueva columna como GENERATED
ALTER TABLE factura_items
ADD COLUMN total DECIMAL(15,2)
GENERATED ALWAYS AS (
    subtotal + COALESCE(total_impuestos, 0)
) STORED
COMMENT 'Total calculado: subtotal + impuestos';

-- 3.3: Eliminar columna vieja
ALTER TABLE factura_items
DROP COLUMN total_old;

-- ============================================================================
-- PASO 4: Verificar que las conversiones fueron exitosas
-- ============================================================================

SELECT
    COLUMN_NAME,
    GENERATION_EXPRESSION,
    EXTRA
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'bd_afe'
  AND TABLE_NAME = 'factura_items'
  AND COLUMN_NAME IN ('subtotal', 'total');

-- Debería mostrar:
-- subtotal | (((`cantidad` * `precio_unitario`) - coalesce(`descuento_valor`,0))) | STORED GENERATED
-- total    | ((`subtotal` + coalesce(`total_impuestos`,0)))                        | STORED GENERATED

SELECT 'CONVERSIÓN COMPLETADA EXITOSAMENTE' AS status;
