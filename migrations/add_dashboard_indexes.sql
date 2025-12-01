-- ============================================================================
-- Índices para optimizar Dashboard con Progressive Disclosure
-- ============================================================================
-- Fecha: 2025-11-30
-- Descripción: Índices compuestos para queries de dashboard optimizado
--
-- Estos índices optimizan las queries de:
-- 1. GET /api/v1/dashboard/mes-actual (mes + año + estado)
-- 2. GET /api/v1/dashboard/alerta-mes (mes + año + estado + count)
-- 3. GET /api/v1/dashboard/historico (mes + año)
--
-- Performance esperada:
-- - Sin índices: O(n) full table scan en 10k+ facturas
-- - Con índices: O(log n) búsqueda indexada
-- ============================================================================

-- ============================================================================
-- 1. ÍNDICE COMPUESTO: (año, mes, estado)
-- ============================================================================
-- Optimiza queries de dashboard principal y alerta
-- Cubre los filtros más comunes:
--   WHERE EXTRACT(year, creado_en) = X
--     AND EXTRACT(month, creado_en) = Y
--     AND estado IN (...)

-- PostgreSQL: Crear índice funcional sobre EXTRACT
CREATE INDEX IF NOT EXISTS idx_facturas_year_month_estado
ON facturas (
    EXTRACT(YEAR FROM creado_en),
    EXTRACT(MONTH FROM creado_en),
    estado
);

-- ============================================================================
-- 2. ÍNDICE COMPUESTO: (creado_en, estado)
-- ============================================================================
-- Optimiza ORDER BY creado_en DESC con filtro de estado
-- Útil para paginación y ordenamiento en dashboard

CREATE INDEX IF NOT EXISTS idx_facturas_creado_estado
ON facturas (creado_en DESC, estado);

-- ============================================================================
-- 3. ÍNDICE PARCIAL: Solo estados activos
-- ============================================================================
-- Optimiza dashboard principal que solo consulta estados activos
-- Índice más pequeño = más rápido

CREATE INDEX IF NOT EXISTS idx_facturas_activas
ON facturas (creado_en DESC)
WHERE estado IN ('en_revision', 'aprobada', 'aprobada_auto', 'rechazada');

-- ============================================================================
-- 4. VERIFICACIÓN DE ÍNDICES CREADOS
-- ============================================================================
-- Query para verificar que los índices fueron creados correctamente

-- PostgreSQL:
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     indexdef
-- FROM pg_indexes
-- WHERE tablename = 'facturas'
--     AND indexname LIKE 'idx_facturas_%'
-- ORDER BY indexname;

-- ============================================================================
-- 5. ANÁLISIS DE PERFORMANCE
-- ============================================================================
-- Ejecutar ANALYZE para actualizar estadísticas del query planner

ANALYZE facturas;

-- ============================================================================
-- 6. TESTING DE ÍNDICES
-- ============================================================================
-- Queries de prueba para verificar que los índices se están usando

-- Test 1: Dashboard mes actual
-- EXPLAIN ANALYZE
-- SELECT *
-- FROM facturas
-- WHERE EXTRACT(YEAR FROM creado_en) = 2025
--   AND EXTRACT(MONTH FROM creado_en) = 11
--   AND estado IN ('en_revision', 'aprobada', 'aprobada_auto', 'rechazada')
-- ORDER BY estado, creado_en DESC;
--
-- Debe mostrar: "Index Scan using idx_facturas_year_month_estado"

-- Test 2: Alerta mes (count)
-- EXPLAIN ANALYZE
-- SELECT COUNT(*)
-- FROM facturas
-- WHERE EXTRACT(YEAR FROM creado_en) = 2025
--   AND EXTRACT(MONTH FROM creado_en) = 11
--   AND estado IN ('en_revision', 'aprobada', 'aprobada_auto');
--
-- Debe mostrar: "Index Only Scan using idx_facturas_year_month_estado"

-- Test 3: Histórico
-- EXPLAIN ANALYZE
-- SELECT *
-- FROM facturas
-- WHERE EXTRACT(YEAR FROM creado_en) = 2025
--   AND EXTRACT(MONTH FROM creado_en) = 10
-- ORDER BY creado_en DESC;
--
-- Debe mostrar: "Index Scan using idx_facturas_year_month_estado"

-- ============================================================================
-- ROLLBACK (si es necesario)
-- ============================================================================
-- Para revertir estos índices en caso de problemas:

-- DROP INDEX IF EXISTS idx_facturas_year_month_estado;
-- DROP INDEX IF EXISTS idx_facturas_creado_estado;
-- DROP INDEX IF EXISTS idx_facturas_activas;

-- ============================================================================
-- NOTAS DE IMPLEMENTACIÓN
-- ============================================================================
--
-- 1. Ejecutar en horario de bajo tráfico (opcional, los índices se crean online)
-- 2. Monitorear tamaño de índices:
--    SELECT pg_size_pretty(pg_relation_size('idx_facturas_year_month_estado'));
-- 3. Performance esperado:
--    - 1k facturas: < 10ms
--    - 10k facturas: < 50ms
--    - 100k facturas: < 200ms
-- 4. Los índices se actualizan automáticamente en INSERT/UPDATE/DELETE
-- 5. VACUUM ANALYZE facturas; (ejecutar mensualmente para mantenimiento)
--
-- ============================================================================
