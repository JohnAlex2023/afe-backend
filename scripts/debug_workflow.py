"""Script de diagnóstico para workflow automático"""
import sys
sys.path.insert(0, '/c/Users/jhont/PRIVADO_ODO/afe-backend')

from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.services.workflow_automatico import WorkflowAutomaticoService
from app.utils.nit_validator import NitValidator
from sqlalchemy import and_

db = SessionLocal()

# Obtener una factura reciente sin workflow
factura = db.query(Factura).filter(
    ~Factura.id.in_(
        db.query(AsignacionNitResponsable.factura_id)
    )
).order_by(Factura.id.desc()).first()

if not factura:
    print("❌ No hay facturas sin workflow")
    sys.exit(1)

print(f"\n📋 Factura: {factura.numero_factura} (ID: {factura.id})")
print(f"   Estado: {factura.estado}")
print(f"   Proveedor ID: {factura.proveedor_id}")

# Obtener NIT
if factura.proveedor:
    nit = factura.proveedor.nit
    print(f"   NIT (desde relación): {nit}")
else:
    print(f"   ❌ Proveedor NO está cargado")
    nit = None

# Validar NIT
if nit:
    es_valido, nit_normalizado = NitValidator.validar_nit(nit)
    print(f"   NIT válido: {es_valido}")
    print(f"   NIT normalizado: {nit_normalizado}")
    
    # Buscar asignaciones
    asignaciones = db.query(AsignacionNitResponsable).filter(
        and_(
            AsignacionNitResponsable.nit == nit_normalizado,
            AsignacionNitResponsable.activo == True
        )
    ).all()
    
    print(f"   Asignaciones encontradas: {len(asignaciones)}")
    for asig in asignaciones:
        print(f"     - Responsable ID: {asig.responsable_id}, Nombre: {asig.nombre_proveedor}")
else:
    print(f"   ❌ NIT es NULL")

# Intentar procesar workflow
print(f"\n🔄 Intentando procesar workflow...")
workflow_service = WorkflowAutomaticoService(db)
resultado = workflow_service.procesar_factura_nueva(factura.id)

print(f"\n📊 Resultado: {resultado}")

db.close()
