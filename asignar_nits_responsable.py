"""
Script para asignar todos los NITs de proveedores al responsable admin
y luego procesar las facturas para crear workflows
"""
from app.db.session import SessionLocal
from app.models.responsable import Responsable
from app.models.proveedor import Proveedor
from app.models.factura import Factura
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.services.workflow_automatico import WorkflowAutomaticoService
from sqlalchemy import distinct

db = SessionLocal()
try:
    # 1. Obtener el responsable admin (alex.taimal)
    admin = db.query(Responsable).filter(Responsable.usuario == 'alex.taimal').first()
    if not admin:
        print("ERROR: No se encontró el responsable admin")
        exit(1)

    print(f"Responsable: {admin.usuario} (ID: {admin.id})")
    print("-" * 60)

    # 2. Obtener todos los proveedores
    proveedores = db.query(Proveedor).all()
    print(f"\nEncontrados {len(proveedores)} proveedores")
    print("-" * 60)

    # 3. Asignar cada NIT al responsable admin
    asignaciones_creadas = 0
    asignaciones_existentes = 0

    for prov in proveedores:
        # Verificar si ya existe la asignación
        asignacion_existente = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.nit == prov.nit,
            AsignacionNitResponsable.responsable_id == admin.id
        ).first()

        if asignacion_existente:
            print(f"  ✓ Ya existe asignación: {prov.nit} - {prov.razon_social}")
            asignaciones_existentes += 1
        else:
            # Crear nueva asignación
            nueva_asignacion = AsignacionNitResponsable(
                nit=prov.nit,
                nombre_proveedor=prov.razon_social,
                responsable_id=admin.id,
                area=prov.area or "General",
                permitir_aprobacion_automatica=True,
                requiere_revision_siempre=False,
                monto_maximo_auto_aprobacion=None,  # Sin límite
                porcentaje_variacion_permitido=5.0,
                activo=True
            )
            db.add(nueva_asignacion)
            print(f"  + Nueva asignación: {prov.nit} - {prov.razon_social}")
            asignaciones_creadas += 1

    db.commit()
    print(f"\n--- Resumen de Asignaciones ---")
    print(f"Asignaciones nuevas creadas: {asignaciones_creadas}")
    print(f"Asignaciones ya existentes: {asignaciones_existentes}")
    print(f"Total de proveedores asignados: {len(proveedores)}")

    # 4. Ahora procesar las facturas para crear workflows
    print("\n" + "=" * 60)
    print("PROCESANDO FACTURAS PARA CREAR WORKFLOWS")
    print("=" * 60)

    facturas = db.query(Factura).all()
    print(f"\nEncontradas {len(facturas)} facturas para procesar")

    servicio = WorkflowAutomaticoService(db)
    procesadas = 0
    errores = 0

    for factura in facturas:
        try:
            # Verificar si ya tiene workflow
            from app.models.workflow_aprobacion import WorkflowAprobacionFactura
            workflow_existente = db.query(WorkflowAprobacionFactura).filter(
                WorkflowAprobacionFactura.factura_id == factura.id
            ).first()

            if workflow_existente:
                print(f"  ○ Factura {factura.id} ({factura.numero_factura}) ya tiene workflow")
                continue

            # Procesar factura
            resultado = servicio.procesar_factura_nueva(factura.id)
            if resultado.get('error'):
                print(f"  ✗ Error en factura {factura.id} ({factura.numero_factura}): {resultado['error']}")
                errores += 1
            else:
                print(f"  ✓ Factura {factura.id} ({factura.numero_factura}) procesada - Estado: {resultado.get('estado')}")
                procesadas += 1
        except Exception as e:
            print(f"  ✗ Excepción procesando factura {factura.id}: {str(e)}")
            errores += 1

    print(f"\n--- Resumen de Procesamiento ---")
    print(f"Facturas procesadas correctamente: {procesadas}")
    print(f"Errores: {errores}")
    print(f"Total de facturas: {len(facturas)}")

finally:
    db.close()

print("\n" + "=" * 60)
print("PROCESO COMPLETADO")
print("=" * 60)
