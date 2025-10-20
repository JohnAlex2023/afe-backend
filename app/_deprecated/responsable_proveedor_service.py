from sqlalchemy.orm import Session
from app.models.proveedor import Proveedor
from app.models.responsable_proveedor import ResponsableProveedor
from app.models.factura import Factura
from sqlalchemy.exc import SQLAlchemyError

def asignar_proveedores_a_responsable(db: Session, responsable_id: int, lista_nit: list[str]):
    resultado = []
    for nit in lista_nit:
        proveedor = db.query(Proveedor).filter_by(nit=nit).first()
        if not proveedor:
            resultado.append({"nit": nit, "status": "Proveedor no encontrado"})
            continue
        rel = db.query(ResponsableProveedor).filter_by(
            responsable_id=responsable_id,
            proveedor_id=proveedor.id
        ).first()
        if not rel:
            rel = ResponsableProveedor(
                responsable_id=responsable_id,
                proveedor_id=proveedor.id,
                activo=True
            )
            db.add(rel)
            resultado.append({"nit": nit, "status": "Asignado"})
        else:
            rel.activo = True
            resultado.append({"nit": nit, "status": "Ya existía, activado"})
        # Actualizar responsable_id en facturas pendientes de ese proveedor
        facturas = db.query(Factura).filter_by(proveedor_id=proveedor.id, responsable_id=None).all()
        for factura in facturas:
            factura.responsable_id = responsable_id
    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise Exception(f"Error en la asignación: {str(e)}")
    return resultado
