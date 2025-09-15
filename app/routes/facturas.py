# app/routers/facturas.py

from typing import List, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import require_responsable
from app.config import get_db
from app.models import Factura, Proveedor
from app.schemas import FacturaSchema

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/facturas", tags=["Facturas"])


# --- Helpers --------------------------------------------------------

def get_factura_or_404(
    db: Session,
    nit_proveedor: str,
    numero_factura: str,
) -> Factura:
    """
    Recupera una factura por NIT y número de factura.
    """
    factura = (
        db.query(Factura)
        .join(Proveedor, Factura.proveedor_id == Proveedor.id)
        .filter(
            Proveedor.nit == nit_proveedor,
            Factura.numero_factura == numero_factura,
        )
        .first()
    )

    if not factura:
        logger.warning("Factura no encontrada (NIT=%s, numero=%s)", nit_proveedor, numero_factura)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")
    return factura


# --- Endpoints ------------------------------------------------------

@router.get("/", response_model=List[FacturaSchema], summary="Listar todas las facturas")
def listar_todas_facturas(db: Session = Depends(get_db)) -> List[FacturaSchema]:
    facturas = db.query(Factura).all()
    logger.info("Se listaron %s facturas en total", len(facturas))
    return facturas


@router.get("/{nit_proveedor}", response_model=List[FacturaSchema], summary="Listar facturas por NIT")
def listar_facturas_por_nit(nit_proveedor: str, db: Session = Depends(get_db)) -> List[FacturaSchema]:
    facturas = (
        db.query(Factura)
        .join(Proveedor, Factura.proveedor_id == Proveedor.id)
        .filter(Proveedor.nit == nit_proveedor)
        .all()
    )
    if not facturas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hay facturas para este NIT")
    logger.info("Se listaron %s facturas para el NIT=%s", len(facturas), nit_proveedor)
    return facturas


@router.get("/{nit_proveedor}/{numero_factura}", response_model=FacturaSchema, summary="Obtener factura por NIT y número")
def obtener_factura_por_nit_y_numero(
    nit_proveedor: str,
    numero_factura: str,
    db: Session = Depends(get_db),
) -> FacturaSchema:
    factura = get_factura_or_404(db, nit_proveedor=nit_proveedor, numero_factura=numero_factura)
    logger.info("Factura recuperada: id=%s", factura.id)
    return factura


@router.post("/{factura_id}/aprobar", summary="Aprobar factura por ID", status_code=status.HTTP_200_OK)
def aprobar_factura(
    factura_id: int,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(require_responsable),
) -> Dict[str, Any]:
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")

    if factura.estado == "aprobada":
        logger.info("Intento de aprobación repetido para factura id=%s", factura.id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La factura ya fue aprobada")

    factura.estado = "aprobada"
    factura.fecha_aprobacion = datetime.utcnow()
    factura.responsable_id = user["id"]

    db.commit()
    db.refresh(factura)

    logger.info("Factura aprobada exitosamente: id=%s por user_id=%s", factura.id, user["id"])
    return {
        "message": "Factura aprobada correctamente",
        "data": FacturaSchema.model_validate(factura),
    }
