# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.proveedor import Proveedor  
from pathlib import Path

db = SessionLocal()

# Obtener todos los NITs que tienen PDFs
base_path = Path(__file__).parent.parent / "invoice_extractor" / "adjuntos"

print("=" * 100)
print("ESCANEANDO TODOS LOS NITs CON PDFs...")
print("=" * 100)

total_matches = 0

for nit_dir in sorted(base_path.iterdir()):
    if not nit_dir.is_dir():
        continue
    
    nit = nit_dir.name
    
    # Obtener PDFs para este NIT
    pdfs = list(nit_dir.glob("fv*.pdf"))
    if not pdfs:
        continue
    
    # Obtener facturas de este NIT
    facturas = db.query(Factura).join(Proveedor).filter(
        Proveedor.nit == nit
    ).all()
    
    if not facturas:
        continue
    
    # Buscar coincidencias
    pdfs_cufes = [f.stem[2:].lower() for f in pdfs]
    
    for f in facturas:
        cufe_lower = f.cufe.lower() if f.cufe else ""
        
        if cufe_lower in pdfs_cufes:
            total_matches += 1
            if total_matches <= 3:  # Mostrar primeras 3
                print(f"\n[MATCH {total_matches}] Factura ID: {f.id}")
                print(f"   Numero: {f.numero_factura}")
                print(f"   NIT: {nit}")
                print(f"   Estado: {f.estado}")
                print(f"   Proveedor: {f.proveedor.razon_social if f.proveedor else 'N/A'}")

print(f"\n" + "=" * 100)
print(f"TOTAL FACTURAS CON PDF: {total_matches}")
print("=" * 100)

db.close()
