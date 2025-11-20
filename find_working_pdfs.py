# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.proveedor import Proveedor
from pathlib import Path

db = SessionLocal()

# Probar con diferentes NITs
nits_a_probar = ['900148265-6', '900156470-3', '900399741-7', '830122566-1', '900032159-4']

print("=" * 100)
print("BUSCANDO FACTURAS CON PDF DISPONIBLE")
print("=" * 100)

facturas_con_pdf = []

for nit in nits_a_probar:
    pdf_dir = Path(__file__).parent.parent / "invoice_extractor" / "adjuntos" / nit
    
    if not pdf_dir.exists():
        continue
    
    # Obtener PDFs disponibles para este NIT
    pdfs_disponibles = [f.stem[2:] for f in pdf_dir.glob("fv*.pdf")]
    
    if not pdfs_disponibles:
        continue
    
    # Buscar facturas de este NIT en BD
    facturas = db.query(Factura).join(Proveedor).filter(
        Proveedor.nit == nit
    ).all()
    
    # Ver si alguna coincide
    for f in facturas:
        cufe_lower = f.cufe.lower() if f.cufe else ""
        if cufe_lower in pdfs_disponibles:
            facturas_con_pdf.append({
                'id': f.id,
                'numero': f.numero_factura,
                'nit': nit,
                'estado': str(f.estado),
                'monto': f.total_calculado
            })
            
            if len(facturas_con_pdf) <= 5:  # Mostrar las primeras 5
                print(f"\n[ENCONTRADA] Factura con PDF disponible:")
                print(f"   ID: {f.id}")
                print(f"   Numero: {f.numero_factura}")
                print(f"   NIT: {nit}")
                print(f"   Estado: {f.estado}")
                print(f"   Monto: ${f.total_calculado:,.2f}" if f.total_calculado else "   Monto: N/A")

print(f"\n" + "=" * 100)
print(f"TOTAL FACTURAS CON PDF DISPONIBLE: {len(facturas_con_pdf)}")
print("=" * 100)

db.close()
