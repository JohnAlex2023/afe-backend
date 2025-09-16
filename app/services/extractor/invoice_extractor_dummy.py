# app/services/extractor/invoice_extractor_dummy.py
from app.services.extractor.base import IInvoiceExtractor
from typing import Iterable
from app.schemas.factura import FacturaCreate
from datetime import date

class DummyExtractor(IInvoiceExtractor):
    def extract(self, batch_size: int = 100) -> Iterable[FacturaCreate]:
        # ejemplo: retorna un par de facturas de prueba
        yield FacturaCreate(
            numero_factura="FAC-DUMMY-001",
            fecha_emision=date.today(),
            cliente_id=None,
            proveedor_id=None,
            subtotal=1000.00,
            iva=190.00,
            total=1190.00,
            moneda="COP",
            fecha_vencimiento=None,
            observaciones="Factura generada por dummy extractor",
            cufe="CUFE-DUMMY-0001",
            total_a_pagar=1190.00
        )
