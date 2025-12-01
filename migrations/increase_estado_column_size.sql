-- Migration: Aumentar tamaño de columna 'estado' en tabla 'facturas'
-- Razón: Soportar nuevos estados: 'validada_contabilidad' (21 chars) y 'devuelta_contabilidad' (22 chars)
-- Fecha: 2025-11-30
-- Ejecutar ANTES de desplegar cambios que usan estos nuevos estados

-- Verificar tamaño actual
-- SELECT COLUMN_NAME, COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS
-- WHERE TABLE_NAME = 'facturas' AND COLUMN_NAME = 'estado';

-- Aumentar de VARCHAR(20) a VARCHAR(30) para soportar todos los estados
ALTER TABLE facturas
MODIFY COLUMN estado VARCHAR(30) NOT NULL DEFAULT 'en_revision';

-- Log de cambio
-- Valores máximos de estado:
-- - en_revision: 11 chars ✓
-- - aprobada: 9 chars ✓
-- - aprobada_auto: 14 chars ✓
-- - rechazada: 9 chars ✓
-- - validada_contabilidad: 21 chars ✓
-- - devuelta_contabilidad: 22 chars ✓ (REQUERÍA AUMENTO)
-- Nuevo límite: 30 chars (con margen de seguridad)
