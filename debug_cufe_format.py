# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.db.session import SessionLocal
from app.models.factura import Factura
from pathlib import Path

db = SessionLocal()

# Obtener una factura cualquiera
factura = db.query(Factura).filter(Factura.cufe != None).first()

print("=" * 100)
print("FORMATO DE CUFE EN BD:")
print("=" * 100)
if factura:
    print(f"Factura ID: {factura.id}")
    print(f"Numero: {factura.numero_factura}")
    print(f"CUFE completo ({len(factura.cufe)} chars):")
    print(factura.cufe)
    print(f"\nCUFE lowercase:")
    print(factura.cufe.lower())
else:
    print("No hay facturas con CUFE")

print("\n" + "=" * 100)
print("FORMATO DE NOMBRE DE PDF EN DISCO:")
print("=" * 100)

# Ver un PDF de ejemplo
pdf_dir = Path(__file__).parent.parent / "invoice_extractor" / "adjuntos" / "811030191-9"
if pdf_dir.exists():
    pdfs = list(pdf_dir.glob("fv*.pdf"))[:3]
    for pdf in pdfs:
        print(f"\nArchivo: {pdf.name}")
        print(f"CUFE extraido (sin 'fv' y sin '.pdf'): {pdf.stem[2:]}")
        print(f"Longitud: {len(pdf.stem[2:])} chars")

db.close()
