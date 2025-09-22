#app/api/v1/routers/responsables.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.responsable import ResponsableCreate, ResponsableRead, ResponsableUpdate
from app.schemas.responsable import ResponsableProveedorAssign, ResponsableProveedorUpdate
from app.schemas.common import ErrorResponse
from app.crud.responsable import get_responsable_by_usuario, create_responsable, update_responsable, delete_responsable
from app.crud.responsable_proveedor import (
    get_proveedores_by_responsable,
    get_responsables_by_proveedor,
    desactivar_responsable_proveedor
)
from sqlalchemy import delete
from app.services.responsable_proveedor_service import asignar_proveedores_a_responsable
from app.utils.logger import logger

router = APIRouter(tags=["Responsables"])

#crear responsable
@router.post(
    "/",
    response_model=ResponsableRead,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
    summary="Crear responsable",
    description="Crea un nuevo usuario responsable en el sistema."
)
def create_responsable_endpoint(
    payload: ResponsableCreate,
    db: Session = Depends(get_db),
):
    if get_responsable_by_usuario(db, payload.usuario):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario ya existe")
    r = create_responsable(db, payload)
    logger.info("Responsable creado", extra={"id": r.id, "usuario": r.usuario})
    return r


# Obtener proveedores asignados a un responsable
@router.get(
    "/{responsable_id}/proveedores",
    summary="Listar proveedores asignados a un responsable"
)
def listar_proveedores_por_responsable(responsable_id: int, db: Session = Depends(get_db)):
    relaciones = get_proveedores_by_responsable(db, responsable_id)
    return [{"proveedor_id": r.proveedor_id, "activo": r.activo, "creado_en": r.creado_en} for r in relaciones]

# Obtener responsables asignados a un proveedor
@router.get(
    "/proveedor/{proveedor_id}/responsables",
    summary="Listar responsables asignados a un proveedor"
)
def listar_responsables_por_proveedor(proveedor_id: int, db: Session = Depends(get_db)):
    relaciones = get_responsables_by_proveedor(db, proveedor_id)
    return [{"responsable_id": r.responsable_id, "activo": r.activo, "creado_en": r.creado_en} for r in relaciones]

# Desactivar relación responsable-proveedor
@router.delete(
    "/{responsable_id}/proveedores/{proveedor_id}",
    summary="Desactivar relación responsable-proveedor"
)
def desactivar_relacion_responsable_proveedor(responsable_id: int, proveedor_id: int, db: Session = Depends(get_db)):
    ok = desactivar_responsable_proveedor(db, responsable_id, proveedor_id)
    if ok:
        return {"msg": "Relación desactivada"}
    else:
        raise HTTPException(status_code=404, detail="Relación no encontrada")

# Eliminar completamente la relación responsable-proveedor
@router.delete(
    "/{responsable_id}/proveedores/{proveedor_id}/eliminar",
    summary="Eliminar completamente la relación responsable-proveedor",
    description="Elimina la fila de la relación responsable-proveedor de la base de datos.",
)
def eliminar_relacion_responsable_proveedor(responsable_id: int, proveedor_id: int, db: Session = Depends(get_db)):
    from app.models.responsable_proveedor import ResponsableProveedor
    from app.models.factura import Factura
    logger.info(f"Intentando eliminar responsable_id={responsable_id}, proveedor_id={proveedor_id}")
    # Buscar la relación aunque esté inactiva
    rel = db.query(ResponsableProveedor).filter(
        ResponsableProveedor.responsable_id == responsable_id,
        ResponsableProveedor.proveedor_id == proveedor_id
    ).first()
    logger.info(f"Resultado de la consulta: {rel}")
    if rel:
        # Log de facturas antes del update para depuración
        facturas = db.query(Factura).filter(
            Factura.proveedor_id == proveedor_id
        ).all()
        logger.info(f"Facturas proveedor_id={proveedor_id}: {[{'id': f.id, 'responsable_id': f.responsable_id} for f in facturas]}")

        # Actualizar facturas: poner responsable_id en NULL donde coincidan ambos IDs (update masivo)
        rows = db.query(Factura).filter(
            Factura.responsable_id == responsable_id,
            Factura.proveedor_id == proveedor_id
        ).update({Factura.responsable_id: None}, synchronize_session=False)
        logger.info(f"Facturas actualizadas: {rows}")
        db.flush()
        db.delete(rel)
        db.commit()
        logger.info(f"Commit realizado. Verificando facturas después del commit...")
        facturas_post = db.query(Factura).filter(
            Factura.proveedor_id == proveedor_id
        ).all()
        logger.info(f"Facturas proveedor_id={proveedor_id} después del commit: {[{'id': f.id, 'responsable_id': f.responsable_id} for f in facturas_post]}")
        logger.info(f"Relación eliminada responsable_id={responsable_id}, proveedor_id={proveedor_id} y facturas actualizadas")
        return {"msg": f"Relación eliminada completamente y facturas actualizadas: {rows}"}
    else:
        logger.warning(f"No se encontró relación responsable_id={responsable_id}, proveedor_id={proveedor_id}")
        raise HTTPException(status_code=404, detail="Relación no encontrada")

#listar responsables

@router.get(
    "/",
    response_model=List[ResponsableRead],
    summary="Listar responsables",
    description="Obtiene todos los responsables registrados."
)
def list_responsables(
    db: Session = Depends(get_db),
):
    from app.models.responsable import Responsable
    return db.query(Responsable).all()


# Asignar proveedores a un responsable
@router.post(
    "/asignar-proveedores",
    status_code=status.HTTP_200_OK,
    summary="Asignar proveedores a responsable",
    description="Asigna uno o varios proveedores (por NIT) a un responsable."
)
def asignar_proveedores_endpoint(
    payload: ResponsableProveedorAssign,
    db: Session = Depends(get_db),
):
    try:
        resultado = asignar_proveedores_a_responsable(db, payload.responsable_id, payload.nits_proveedores)
        return {"msg": "Asignación realizada", "detalle": resultado}
    except Exception as e:
        logger.error(f"Error en asignación de proveedores: {e}")
        raise HTTPException(status_code=400, detail=str(e))

#actualizar responsable
@router.put(
    "/{responsable_id}/proveedores",
    summary="Actualizar NITs asignados a un responsable",
    description="Actualiza la lista de NITs de proveedores asignados a un responsable. La asignación es idempotente: activa los NITs enviados y desactiva los que ya no estén.",
)
def actualizar_proveedores_responsable(
    responsable_id: int,
    payload: ResponsableProveedorUpdate,
    db: Session = Depends(get_db),
):
    # Obtener todos los proveedores actualmente asignados
    actuales = get_proveedores_by_responsable(db, responsable_id)
    actuales_nits = set()
    from app.models.proveedor import Proveedor
    for rel in actuales:
        prov = db.query(Proveedor).filter_by(id=rel.proveedor_id).first()
        if prov:
            actuales_nits.add(prov.nit)
    nuevos_nits = set(payload.nits_proveedores)
    # Desactivar los que ya no estén
    for rel in actuales:
        prov = db.query(Proveedor).filter_by(id=rel.proveedor_id).first()
        if prov and prov.nit not in nuevos_nits:
            rel.activo = False
    # Asignar/activar los nuevos
    resultado = asignar_proveedores_a_responsable(db, responsable_id, list(nuevos_nits))
    return {"msg": "Asignación actualizada", "detalle": resultado}
@router.put(
    "/{id}",
    response_model=ResponsableRead,
    responses={404: {"model": ErrorResponse}},
    summary="Actualizar responsable",
    description="Actualiza los datos de un responsable por su ID."
)
def update_responsable_endpoint(
    id: int,
    payload: ResponsableUpdate,
    db: Session = Depends(get_db),
):
    r = update_responsable(db, id, payload)
    if not r:
        raise HTTPException(status_code=404, detail="Responsable no encontrado")
    logger.info("Responsable actualizado", extra={"id": r.id, "usuario": r.usuario})
    return r

#eliminar responsable

@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
    summary="Eliminar responsable",
    description="Elimina un responsable por su ID."
)
def delete_responsable_endpoint(
    id: int,
    db: Session = Depends(get_db),
):
    ok = delete_responsable(db, id)
    if not ok:
        raise HTTPException(status_code=404, detail="Responsable no encontrado")
    logger.info("Responsable eliminado", extra={"id": id})
    return None