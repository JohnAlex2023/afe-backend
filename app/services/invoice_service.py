# app/services/invoice_service.py
from sqlalchemy.orm import Session
from app.crud.factura import create_factura, find_by_cufe, find_by_numero_proveedor, update_factura
from app.crud.audit import create_audit
from app.schemas.factura import FacturaCreate
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

def process_and_persist_invoice(db: Session, payload: FacturaCreate, created_by: str) -> Tuple[dict, str]:
    data = payload.dict()

    # Validar que total y total_a_pagar estén presentes, no se calculan aquí
    if data.get("total") is None:
        raise ValueError("El campo 'total' es obligatorio y debe venir en la factura.")
    if data.get("total_a_pagar") is None:
        raise ValueError("El campo 'total_a_pagar' es obligatorio y debe venir en la factura.")

    # Deduplicación por CUFE
    existing = find_by_cufe(db, data["cufe"])
    if existing:
        changed_fields = {}
        for key in ["subtotal", "iva", "total", "total_a_pagar", "observaciones"]:
            if getattr(existing, key) != data.get(key):
                changed_fields[key] = data.get(key)
        if changed_fields:
            inv = update_factura(db, existing, changed_fields)
            create_audit(
                db, "factura", inv.id, "update", created_by,
                {"reason": "update on existing cufe", "changes": changed_fields}
            )
            return {"id": inv.id, "action": "updated"}, "updated"
        return {"id": existing.id, "action": "ignored"}, "ignored"

    # Deduplicación por número + proveedor
    if data.get("proveedor_id") is not None:
        existing2 = find_by_numero_proveedor(db, data["numero_factura"], data["proveedor_id"])
        if existing2:
            if existing2.cufe != data["cufe"]:
                create_audit(
                    db,
                    "factura",
                    existing2.id,
                    "conflict",
                    created_by,
                    {
                        "msg": "numero/proveedor exists with different cufe",
                        "existing_cufe": existing2.cufe,
                        "incoming_cufe": data["cufe"],
                    },
                )
                return {"id": existing2.id, "action": "conflict"}, "conflict"
            return {"id": existing2.id, "action": "ignored"}, "ignored"

    # Crear nueva factura
    inv = create_factura(db, data)
    create_audit(
        db,
        "factura",
        inv.id,
        "create",
        created_by,
        {"msg": "Nueva factura creada desde Microsoft Graph"}
    )

    # 🚀 ACTIVAR WORKFLOW AUTOMÁTICO PARA LA NUEVA FACTURA
    try:
        from app.services.workflow_automatico import WorkflowAutomaticoService
        workflow_service = WorkflowAutomaticoService(db)
        workflow_resultado = workflow_service.procesar_factura_nueva(inv.id)

        if workflow_resultado.get("exito"):
            logger.info(f"✅ Workflow creado para factura {inv.id}: {workflow_resultado.get('tipo_aprobacion', 'N/A')}")
        else:
            logger.warning(f"⚠️ Workflow creado con advertencia para factura {inv.id}: {workflow_resultado.get('mensaje', 'Sin mensaje')}")

    except Exception as e:
        logger.error(f"❌ Error al crear workflow para factura {inv.id}: {str(e)}")
        # No falla la creación de la factura si el workflow falla
        create_audit(
            db,
            "workflow",
            inv.id,
            "error",
            "SISTEMA",
            {"error": str(e), "msg": "Error al crear workflow automático"}
        )

    return {"id": inv.id, "action": "created"}, "created"


