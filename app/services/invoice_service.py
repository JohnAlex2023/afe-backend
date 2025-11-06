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

    # ENTERPRISE PATTERN: ACTIVAR WORKFLOW AUTOMÁTICO
    # El workflow es CRÍTICO para la operación correcta del sistema.
    # Si falla, debemos saberlo inmediatamente.
    try:
        from app.services.workflow_automatico import WorkflowAutomaticoService
        workflow_service = WorkflowAutomaticoService(db)

        logger.info(f"🔄 Iniciando workflow automático para factura {inv.id}")
        workflow_resultado = workflow_service.procesar_factura_nueva(inv.id)
        logger.info(f"📋 Resultado del workflow: {workflow_resultado}")

        if workflow_resultado.get("exito"):
            logger.info(
                f" Workflow creado exitosamente para factura {inv.id}",
                extra={
                    "factura_id": inv.id,
                    "responsable_id": workflow_resultado.get('responsable_id'),
                    "nit": workflow_resultado.get('nit'),
                    "tipo_aprobacion": workflow_resultado.get('tipo_aprobacion', 'N/A')
                }
            )
        else:
            # Workflow creado pero con advertencias (ej: NIT sin asignación)
            logger.warning(
                f"⚠️  Workflow NO se creó para factura {inv.id}. Resultado: {workflow_resultado}",
                extra={
                    "factura_id": inv.id,
                    "error": workflow_resultado.get('error'),
                    "nit": workflow_resultado.get('nit'),
                    "mensaje": workflow_resultado.get('mensaje'),
                    "requiere_configuracion": workflow_resultado.get('requiere_configuracion', False)
                }
            )

            # Registrar en auditoría para visibilidad
            create_audit(
                db,
                "workflow",
                inv.id,
                "warning",
                "SISTEMA",
                {
                    "msg": "Workflow no se creó - requiere configuración",
                    "resultado_completo": workflow_resultado,
                    "nit": workflow_resultado.get('nit'),
                    "requiere_configuracion": workflow_resultado.get('requiere_configuracion', False)
                }
            )

    except Exception as e:
        # ❌ CRITICAL: El workflow falló completamente
        logger.error(
            f"❌ ERROR CRÍTICO al crear workflow para factura {inv.id}: {str(e)}",
            extra={
                "factura_id": inv.id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True  # Incluir stack trace completo
        )

        # Registrar en auditoría con severidad alta
        create_audit(
            db,
            "workflow",
            inv.id,
            "error",
            "SISTEMA",
            {
                "error": str(e),
                "error_type": type(e).__name__,
                "msg": "Error crítico al crear workflow automático",
                "severity": "CRITICAL"
            }
        )

        # ⚠️ ENTERPRISE DECISION:
        # NO fallar la creación de la factura (datos financieros no se pierden)
        # PERO el error queda registrado y visible para corrección manual

    return {"id": inv.id, "action": "created"}, "created"


