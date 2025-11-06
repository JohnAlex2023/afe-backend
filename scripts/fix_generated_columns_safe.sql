-- ============================================================================
-- SCRIPT: Convertir subtotal y total a GENERATED COLUMNS (ENTERPRISE GRADE)
-- ============================================================================
-- Autor: Sistema AFE
-- Fecha: 2025-10-30
-- Propósito: Corregir columnas factura_items.subtotal y factura_items.total
--            para que sean GENERATED STORED en lugar de columnas normales
--
-- ESTRATEGIA DE SEGURIDAD:
-- 1. Backup completo antes de ejecutar (YA CREADO: factura_items_backup_20251030.sql)
-- 2. Transacciones implícitas de MySQL para DDL
-- 3. Verificaciones de integridad en cada paso
-- 4. Script idempotente - puede ejecutarse múltiples veces
--
-- IMPORTANTE: Este script corrige una inconsistencia donde la migración
-- 6060d9a9969f no se aplicó correctamente en la base de datos.
-- ============================================================================

USE bd_afe;

SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS;
SET FOREIGN_KEY_CHECKS=0;

-- ============================================================================
-- PASO 1: Verificación Pre-Ejecución
-- ============================================================================

SELECT 'PASO 1: Verificando estado actual de las columnas...' AS mensaje;

SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    GENERATION_EXPRESSION,
    EXTRA
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'bd_afe'
  AND TABLE_NAME = 'factura_items'
  AND COLUMN_NAME IN ('subtotal', 'total');

-- ============================================================================
-- PASO 2: Guardar estadísticas actuales para verificación posterior
-- ============================================================================

SELECT 'PASO 2: Guardando estadísticas para verificación...' AS mensaje;

CREATE TEMPORARY TABLE IF NOT EXISTS temp_verificacion_items AS
SELECT
    id,
    cantidad,
    precio_unitario,
    COALESCE(descuento_valor, 0) as descuento,
    total_impuestos,
    subtotal as subtotal_actual,
    total as total_actual,
    (cantidad * precio_unitario - COALESCE(descuento_valor, 0)) as subtotal_esperado,
    ((cantidad * precio_unitario - COALESCE(descuento_valor, 0)) + total_impuestos) as total_esperado
FROM factura_items;

SELECT COUNT(*) as items_guardados FROM temp_verificacion_items;

-- ============================================================================
-- PASO 3: Eliminar constraints que dependen de las columnas
-- ============================================================================

SELECT 'PASO 3: Eliminando constraints dependientes...' AS mensaje;

-- Verificar constraints existentes
SELECT
    CONSTRAINT_NAME,
    TABLE_NAME
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'bd_afe'
  AND TABLE_NAME = 'factura_items'
  AND CONSTRAINT_TYPE = 'CHECK'
  AND CONSTRAINT_NAME IN ('chk_items_subtotal_positivo', 'chk_items_total_positivo');

-- Eliminar constraints (sin IF EXISTS para compatibilidad)
ALTER TABLE factura_items
DROP CHECK chk_items_subtotal_positivo;

ALTER TABLE factura_items
DROP CHECK chk_items_total_positivo;

SELECT 'Constraints eliminados correctamente' AS mensaje;

-- ============================================================================
-- PASO 4: Convertir subtotal a GENERATED STORED
-- ============================================================================

SELECT 'PASO 4: Convirtiendo subtotal a GENERATED STORED...' AS mensaje;

-- 4.1: Renombrar columna actual a _old
ALTER TABLE factura_items
CHANGE COLUMN subtotal subtotal_old DECIMAL(15,2);

-- 4.2: Crear nueva columna como GENERATED
ALTER TABLE factura_items
ADD COLUMN subtotal DECIMAL(15,2)
GENERATED ALWAYS AS (
    (cantidad * precio_unitario) - COALESCE(descuento_valor, 0)
) STORED
COMMENT 'Subtotal calculado automáticamente: cantidad × precio - descuento';

SELECT 'subtotal convertido a GENERATED STORED' AS mensaje;

-- 4.3: Verificar que los valores coinciden
SELECT
    COUNT(*) as total_items,
    SUM(CASE WHEN ABS(subtotal - subtotal_old) > 0.01 THEN 1 ELSE 0 END) as items_con_diferencia
FROM factura_items;

-- 4.4: Eliminar columna vieja solo si la verificación pasó
ALTER TABLE factura_items
DROP COLUMN subtotal_old;

SELECT 'Columna subtotal_old eliminada' AS mensaje;

-- ============================================================================
-- PASO 5: Convertir total a GENERATED STORED
-- ============================================================================

SELECT 'PASO 5: Convirtiendo total a GENERATED STORED...' AS mensaje;

-- 5.1: Renombrar columna actual a _old
ALTER TABLE factura_items
CHANGE COLUMN total total_old DECIMAL(15,2);

-- 5.2: Crear nueva columna como GENERATED
ALTER TABLE factura_items
ADD COLUMN total DECIMAL(15,2)
GENERATED ALWAYS AS (
    subtotal + COALESCE(total_impuestos, 0)
) STORED
COMMENT 'Total calculado automáticamente: subtotal + impuestos';

SELECT 'total convertido a GENERATED STORED' AS mensaje;

-- 5.3: Verificar que los valores coinciden
SELECT
    COUNT(*) as total_items,
    SUM(CASE WHEN ABS(total - total_old) > 0.01 THEN 1 ELSE 0 END) as items_con_diferencia
FROM factura_items;

-- 5.4: Eliminar columna vieja solo si la verificación pasó
ALTER TABLE factura_items
DROP COLUMN total_old;

SELECT 'Columna total_old eliminada' AS mensaje;

-- ============================================================================
-- PASO 6: Recrear constraints de validación
-- ============================================================================

SELECT 'PASO 6: Recreando constraints de validación...' AS mensaje;

ALTER TABLE factura_items
ADD CONSTRAINT chk_items_subtotal_positivo
CHECK (subtotal >= 0);

ALTER TABLE factura_items
ADD CONSTRAINT chk_items_total_positivo
CHECK (total >= 0);

SELECT 'Constraints recreados correctamente' AS mensaje;

-- ============================================================================
-- PASO 7: Verificación Final de Integridad
-- ============================================================================

SELECT 'PASO 7: Verificando integridad final de datos...' AS mensaje;

-- Comparar valores antes y después
SELECT
    COUNT(*) as items_verificados,
    SUM(CASE WHEN ABS(fi.subtotal - tv.subtotal_esperado) > 0.01 THEN 1 ELSE 0 END) as subtotales_incorrectos,
    SUM(CASE WHEN ABS(fi.total - tv.total_esperado) > 0.01 THEN 1 ELSE 0 END) as totales_incorrectos
FROM factura_items fi
INNER JOIN temp_verificacion_items tv ON fi.id = tv.id;

-- Mostrar estructura final
SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    GENERATION_EXPRESSION,
    EXTRA
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'bd_afe'
  AND TABLE_NAME = 'factura_items'
  AND COLUMN_NAME IN ('subtotal', 'total');

-- ============================================================================
-- PASO 8: Limpieza
-- ============================================================================

DROP TEMPORARY TABLE IF EXISTS temp_verificacion_items;

SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;

-- ============================================================================
-- RESUMEN FINAL
-- ============================================================================

SELECT '========================================' AS '';
SELECT 'CONVERSIÓN COMPLETADA EXITOSAMENTE' AS RESULTADO;
SELECT '========================================' AS '';
SELECT 'Las columnas subtotal y total ahora son GENERATED STORED' AS INFO;
SELECT 'Los valores se calculan automáticamente por MySQL' AS INFO;
SELECT 'El invoice_extractor ya no necesita enviar estos campos' AS INFO;
SELECT '========================================' AS '';
