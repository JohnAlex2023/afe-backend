from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import and_

from app.models.factura import Factura
from app.models.proveedor import Proveedor
from app.models.responsable import Responsable
from app.models.cliente import Cliente
from app.models.responsable import ResponsableNit


# -----------------------------------------------------
# Obtener factura por ID
# -----------------------------------------------------
def get_factura(db: Session, factura_id: int) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.id == factura_id).first()


# -----------------------------------------------------
# Listar facturas (con filtros opcionales)
# -----------------------------------------------------
def list_facturas(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    nit: Optional[str] = None,
    numero_factura: Optional[str] = None,
) -> List[Factura]:
    query = db.query(Factura)

    if nit:
        # Hacemos JOIN con Proveedor y filtramos por NIT
        query = query.join(Proveedor).filter(Proveedor.nit == nit)

    if numero_factura:
        query = query.filter(Factura.numero_factura == numero_factura)

    return query.offset(skip).limit(limit).all()


# -----------------------------------------------------
# Buscar por CUFE
# -----------------------------------------------------
def find_by_cufe(db: Session, cufe: str) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.cufe == cufe).first()


# -----------------------------------------------------
# Buscar por número de factura
# -----------------------------------------------------
def get_factura_by_numero(db: Session, numero_factura: str) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.numero_factura == numero_factura).first()


# -----------------------------------------------------
# Buscar por número de factura y proveedor
# -----------------------------------------------------
def find_by_numero_proveedor(db: Session, numero: str, proveedor_id: int) -> Optional[Factura]:
    return (
        db.query(Factura)
        .filter(
            and_(
                Factura.numero_factura == numero,
                Factura.proveedor_id == proveedor_id
            )
        )
        .first()
    )



# -----------------------------------------------------
# Crear factura con asignación automática de responsable
# -----------------------------------------------------
def create_factura(db: Session, data: dict) -> Factura:
    obj = Factura(**data)

    # --- asignar responsable automáticamente ---
    if obj.proveedor_id:
        proveedor = db.query(Proveedor).filter(Proveedor.id == obj.proveedor_id).first()
        if proveedor and proveedor.nit:
            resp_nit = db.query(ResponsableNit).filter(ResponsableNit.nit == proveedor.nit).first()
            if resp_nit:
                obj.responsable_id = resp_nit.responsable_id

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj




# -----------------------------------------------------
# Actualizar factura y re-asignar responsable
# -----------------------------------------------------
def update_factura(db: Session, factura: Factura, fields: dict) -> Factura:
    for k, v in fields.items():
        setattr(factura, k, v)

    # --- reasignar responsable si cambia proveedor ---
    if factura.proveedor_id:
        proveedor = db.query(Proveedor).filter(Proveedor.id == factura.proveedor_id).first()
        if proveedor and proveedor.nit:
            resp_nit = db.query(ResponsableNit).filter(ResponsableNit.nit == proveedor.nit).first()
            if resp_nit:
                factura.responsable_id = resp_nit.responsable_id

    db.add(factura)
    db.commit()
    db.refresh(factura)
    return factura

# -----------------------------------------------------
# Asignar responsables pendientes (stub temporal)
# -----------------------------------------------------
def asignar_responsables_pendientes(db: Session) -> int:
    # Implementación real pendiente
    return 0


