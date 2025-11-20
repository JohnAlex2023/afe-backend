-- ============================================================================
-- MIGRACIÓN: Agregar rol CONTADOR
-- Fecha: 2025-11-18
-- Descripción: Agrega el rol "contador" al sistema para usuarios de contabilidad
-- ============================================================================

-- Verificar si el rol ya existe antes de insertar
INSERT INTO roles (nombre)
SELECT 'contador'
WHERE NOT EXISTS (
    SELECT 1 FROM roles WHERE nombre = 'contador'
);

-- Verificar resultado
SELECT * FROM roles WHERE nombre = 'contador';
