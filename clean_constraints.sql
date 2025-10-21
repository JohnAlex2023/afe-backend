-- Eliminar constraints que quedaron del intento fallido
USE afe_dev;

-- Facturas
ALTER TABLE facturas DROP CONSTRAINT IF EXISTS chk_facturas_subtotal_positivo;
ALTER TABLE facturas DROP CONSTRAINT IF EXISTS chk_facturas_iva_positivo;
ALTER TABLE facturas DROP CONSTRAINT IF EXISTS chk_facturas_aprobada_con_aprobador;
ALTER TABLE facturas DROP CONSTRAINT IF EXISTS chk_facturas_rechazada_con_motivo;

-- Factura items
ALTER TABLE factura_items DROP CONSTRAINT IF EXISTS chk_items_cantidad_positiva;
ALTER TABLE factura_items DROP CONSTRAINT IF EXISTS chk_items_precio_positivo;
ALTER TABLE factura_items DROP CONSTRAINT IF EXISTS chk_items_subtotal_positivo;
ALTER TABLE factura_items DROP CONSTRAINT IF EXISTS chk_items_total_positivo;
ALTER TABLE factura_items DROP CONSTRAINT IF EXISTS chk_items_descuento_valido;

-- Proveedores
ALTER TABLE proveedores DROP CONSTRAINT IF EXISTS chk_proveedores_nit_no_vacio;

SELECT 'Constraints eliminados exitosamente' AS status;
