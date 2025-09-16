# app/services/invoice_service.py
from sqlalchemy.orm import Session
from app.crud.factura import create_factura, find_by_cufe, find_by_numero_proveedor, update_factura, get_factura
from app.crud.audit import create_audit
from app.schemas.factura import FacturaCreate
from typing import Tuple

def process_and_persist_invoice(db: Session, payload: FacturaCreate, created_by: str) -> Tuple[dict, str]:
    # normalizar/calcular total
    data = payload.dict()
    if data.get("total") is None:
        data["total"] = round(data.get("subtotal", 0.0) + data.get("iva", 0.0), 2)
    if data.get("total_a_pagar") is None:
        data["total_a_pagar"] = data["total"]

    # deduplicación por cufe
    existing = find_by_cufe(db, data["cufe"])
    if existing:
        # actualizar si cambió
        changed_fields = {}
        for key in ["subtotal", "iva", "total", "total_a_pagar", "observaciones"]:
            if getattr(existing, key) != data.get(key):
                changed_fields[key] = data.get(key)
        if changed_fields:
            inv = update_factura(db, existing, changed_fields)
            create_audit(db, "factura", inv.id, "update", created_by, {"reason": "update on existing cufe", "changes": changed_fields})
            return {"id": inv.id, "action": "updated"}, "updated"
        return {"id": existing.id, "action": "ignored"}, "ignored"

    # dedupe por numero+proveedor
    if data.get("proveedor_id") is not None:
        existing2 = find_by_numero_proveedor(db, data["numero_factura"], data["proveedor_id"])
        if existing2:
            # si cufe distinto, crear auditoría
            if existing2.cufe != data["cufe"]:
                create_audit(db, "factura", existing2.id, "conflict", created_by, {"msg": "numero/proveedor exists with different cufe", "existing_cufe": existing2.cufe, "incoming_cufe": data["cufe"]})
                return {"id": existing2.id, "action": "conflict"}, "conflict"
            return {"id": existing2.id, "action": "ignored"}, "ignored"

    inv = create_factura(db, data)
    create_audit(db, "factura", inv.id, "create", created_by, {"source": "ingest"})
    return {"id": inv.id, "action": "created"}, "created"
