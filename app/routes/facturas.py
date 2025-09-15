# ...existing imports...
# ...existing code...

# --- Endpoints ------------------------------------------------------

# app/routers/facturas.py

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import require_responsable
from app.config import get_db
from app.models import Factura, Proveedor
from app.schemas import FacturaSchema

logger = logging.getLogger(__name__)
router = APIRouter()  # El prefix se define en main.py

# --- Endpoints ------------------------------------------------------

@router.get("/por-numero/{numero_factura}", response_model=FacturaSchema, summary="Obtener factura por número de factura")
def obtener_factura_por_numero(numero_factura: str, db: Session = Depends(get_db)) -> FacturaSchema:
    factura = db.query(Factura).filter(Factura.numero_factura == numero_factura).first()
    if not factura:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")
    return factura


def get_factura_or_404(
    db: Session,
    nit_proveedor: Optional[str] = None,
    numero_factura: Optional[str] = None,
    proveedor_id: Optional[int] = None,
) -> Factura:
    """
    Recupera una factura según los parámetros proporcionados.
    Lanza un HTTP 404 si no existe.
    """
    query = db.query(Factura)

    if nit_proveedor and numero_factura:
        query = (
            query.join(Proveedor, Factura.proveedor_id == Proveedor.id)
            .filter(
                Proveedor.nit == nit_proveedor,
                Factura.numero_factura == numero_factura,
            )
        )
    elif numero_factura:
        query = query.filter(Factura.numero_factura == numero_factura)
    elif proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    factura = query.first()
    if not factura:
        logger.warning(
            "Factura no encontrada. Params -> nit_proveedor=%s, numero_factura=%s, proveedor_id=%s",
            nit_proveedor,
            numero_factura,
            proveedor_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada",
        )
    return factura


# --- Endpoints ------------------------------------------------------

@router.get(
    "/{nit_proveedor}/{numero_factura}",
    response_model=FacturaSchema,
    summary="Obtener factura por NIT y número",
)
def obtener_factura_por_nit_numero(
    nit_proveedor: str,
    numero_factura: str,
    db: Session = Depends(get_db),
) -> FacturaSchema:
    """
    Recupera una factura específica por NIT de proveedor y número de factura.
    """
    factura = get_factura_or_404(db, nit_proveedor=nit_proveedor, numero_factura=numero_factura)
    logger.info("Factura recuperada: id=%s", factura.id)
    return factura


@router.post(
    "/{nit_proveedor}/{numero_factura}/aprobar",
    summary="Aprobar factura por NIT y número",
    status_code=status.HTTP_200_OK,
)
def aprobar_factura(
    nit_proveedor: str,
    numero_factura: str,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_responsable),
) -> Dict[str, Any]:
    """
    Aprueba una factura por NIT y número.
    Requiere rol 'responsable'.
    """
    factura = get_factura_or_404(db, nit_proveedor=nit_proveedor, numero_factura=numero_factura)

    if getattr(factura, "estado_aprobacion", None) == "aprobada":
        logger.info("Intento de aprobación repetido para factura id=%s", factura.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La factura ya fue aprobada",
        )

    factura.estado_aprobacion = "aprobada"
    factura.fecha_aprobacion = datetime.utcnow()
    factura.responsable_id = user["id"]

    db.commit()
    db.refresh(factura)

    logger.info("Factura aprobada exitosamente: id=%s por user_id=%s", factura.id, user["id"])
    return {
        "message": "Factura aprobada correctamente",
        "data": FacturaSchema.model_validate(factura),
    }


@router.get(
    "/por-nit/{nit_proveedor}",
    response_model=List[FacturaSchema],
    summary="Listar facturas por NIT",
)
def listar_facturas_por_nit(
    nit_proveedor: str,
    db: Session = Depends(get_db),
) -> List[FacturaSchema]:
    """
    Lista todas las facturas asociadas a un NIT de proveedor.
    """
    facturas = (
        db.query(Factura)
        .join(Proveedor, Factura.proveedor_id == Proveedor.id)
        .filter(Proveedor.nit == nit_proveedor)
        .all()
    )
    logger.info("Se listaron %s facturas para el NIT=%s", len(facturas), nit_proveedor)
    return facturas


@router.get(
    "/proveedor/{proveedor_id}",
    response_model=List[FacturaSchema],
    summary="Listar facturas por proveedor (ID)",
)
def listar_facturas_por_proveedor(
    proveedor_id: int,
    db: Session = Depends(get_db),
) -> List[FacturaSchema]:
    """
    Lista todas las facturas asociadas a un proveedor por su ID.
    """
    facturas = db.query(Factura).filter(Factura.proveedor_id == proveedor_id).all()
    logger.info("Se listaron %s facturas para el proveedor_id=%s", len(facturas), proveedor_id)
    return facturas


@router.get(
    "/",
    response_model=List[FacturaSchema],
    summary="Listar todas las facturas",
)
def listar_todas_facturas(db: Session = Depends(get_db)):
    """
    Lista todas las facturas en el sistema.
    """
    facturas = db.query(Factura).all()
    logger.info("Se listaron %s facturas en total", len(facturas))
    return facturas

@router.get("/{factura_id}", response_model=FacturaSchema, summary="Obtener factura por ID")
def obtener_factura_por_id(factura_id: int, db: Session = Depends(get_db)) -> FacturaSchema:
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")
    return factura
