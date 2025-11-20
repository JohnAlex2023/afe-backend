# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.proveedor import Proveedor
from pathlib import Path

db = SessionLocal()

# Path al directorio de PDFs
pdf_dir = Path(__file__).parent.parent / "invoice_extractor" / "adjuntos" / "811030191-9"

# Listar PDFs disponibles
pdfs_disponibles = []
if pdf_dir.exists():
    pdfs_disponibles = [f.stem[2:] for f in pdf_dir.glob("fv*.pdf")]  # Quitar prefijo 'fv'
    print(f"PDFs disponibles en disco: {len(pdfs_disponibles)}")

print("\n" + "=" * 100)

# Buscar facturas del NIT 811030191-9
facturas = db.query(Factura).join(Proveedor).filter(
    Proveedor.nit == '811030191-9'
).all()

print(f"Facturas en BD: {len(facturas)}")
print("=" * 100)

# Verificar qué facturas tienen PDF
for f in facturas:
    cufe_lower = f.cufe.lower() if f.cufe else ""
    tiene_pdf = cufe_lower in pdfs_disponibles
    
    marca = "[SI PDF]" if tiene_pdf else "[NO PDF]"
    print(f"\n{marca} Factura {f.numero_factura} (ID: {f.id})")
    print(f"   Estado: {f.estado}")
    print(f"   Monto: ${f.total_calculado:,.2f}" if f.total_calculado else "   Monto: N/A")
    if f.cufe:
        print(f"   CUFE: {f.cufe[:50]}...")

db.close()
