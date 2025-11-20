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
    print("Primeros 5 CUFEs de PDFs:", pdfs_disponibles[:5])
else:
    print("Directorio de PDFs no encontrado")

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
    
    print(f"\n{'✅' if tiene_pdf else '❌'} Factura {f.numero_factura} (ID: {f.id})")
    print(f"   Estado: {f.estado}")
    print(f"   Tiene PDF: {'SÍ' if tiene_pdf else 'NO'}")
    if f.cufe:
        print(f"   CUFE: {f.cufe[:50]}...")

db.close()
