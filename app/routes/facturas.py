from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import require_responsable
from app.config import get_db
from app.models import Factura
from app.schemas import FacturaSchema

router = APIRouter()


@router.get(
    "/{nit_proveedor}/{numero_factura}",
    response_model=FacturaSchema,
    summary="Obtener factura por NIT y número"
)
def get_factura_por_nit_numero(
    nit_proveedor: str,
    numero_factura: str,
    db: Session = Depends(get_db)
) -> FacturaSchema:
    """
    Devuelve una factura filtrada por **nit_proveedor** y **numero_factura**.
    """
    factura = (
        db.query(Factura)
        .filter(
            Factura.nit_proveedor == nit_proveedor,
            Factura.numero_factura == numero_factura,
        )
        .first()
    )

    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada",
        )

    return factura


@router.post(
    "/{nit_proveedor}/{numero_factura}/aprobar",
    summary="Aprobar factura por NIT y número"
)
def aprobar_factura_por_nit_numero(
    nit_proveedor: str,
    numero_factura: str,
    db: Session = Depends(get_db),
    user=Depends(require_responsable)
):
    """
    Aprueba una factura según **nit_proveedor** y **numero_factura**.
    Solo puede hacerlo un usuario con rol de responsable.
    """
    factura = (
        db.query(Factura)
        .filter(
            Factura.nit_proveedor == nit_proveedor,
            Factura.numero_factura == numero_factura,
        )
        .first()
    )

    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada",
        )

    if factura.estado_aprobacion == "aprobada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La factura ya fue aprobada",
        )

    factura.estado_aprobacion = "aprobada"
    factura.fecha_aprobacion = datetime.now()
    factura.responsable_id = user["id"]

    db.commit()
    db.refresh(factura)

    return {
        "message": "Factura aprobada",
        "factura_id": factura.id,
        "responsable_id": user["id"],
    }
