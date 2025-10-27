-- ============================================================
-- SCRIPT: Limpiar tabla asignacion_nit_responsable y reiniciar IDs
-- ============================================================
--
-- Este script:
-- 1. Elimina TODOS los registros de la tabla
-- 2. Reinicia el auto-increment al valor inicial (1)
-- 3. Verifica que la tabla esté limpia
--
-- ADVERTENCIA: Esta operación es IRREVERSIBLE
-- Hacer backup antes de ejecutar
-- ============================================================

-- PASO 1: Eliminar TODOS los registros
DELETE FROM bd_afe.asignacion_nit_responsable;

-- PASO 2: Reiniciar auto-increment
-- Para MySQL/MariaDB:
ALTER TABLE bd_afe.asignacion_nit_responsable AUTO_INCREMENT = 1;

-- PASO 3: Verificar que está limpia
SELECT COUNT(*) as total_registros FROM bd_afe.asignacion_nit_responsable;

-- PASO 4: Ver estructura de la tabla
DESCRIBE bd_afe.asignacion_nit_responsable;

-- ============================================================
-- RESULTADO ESPERADO:
-- - total_registros: 0
-- - next_auto_increment: 1
-- ============================================================
