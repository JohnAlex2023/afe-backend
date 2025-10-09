from app.db.base import Base

# Importa modelos para que se registren en Base.metadata
from .cliente import Cliente
from .proveedor import Proveedor
from .factura import Factura
from .responsable import Responsable
from .responsable_proveedor import ResponsableProveedor
from .role import Role
from .audit_log import AuditLog
from .usuario import Usuario
from .importacion_presupuesto import ImportacionPresupuesto
from .presupuesto import LineaPresupuesto, EjecucionPresupuestal
from .workflow_aprobacion import (
    WorkflowAprobacionFactura,
    AsignacionNitResponsable,
    NotificacionWorkflow,
    ConfiguracionCorreo
)
from .historial_pagos import HistorialPagos, TipoPatron
from .automation_audit import (
    AutomationAudit,
    AutomationMetrics,
    ConfiguracionAutomatizacion,
    ProveedorTrust
)

__all__ = [
    "Cliente",
    "Proveedor",
    "Factura",
    "Responsable",
    "ResponsableProveedor",
    "Role",
    "AuditLog",
    "Usuario",
    "ImportacionPresupuesto",
    "LineaPresupuesto",
    "EjecucionPresupuestal",
    "WorkflowAprobacionFactura",
    "AsignacionNitResponsable",
    "NotificacionWorkflow",
    "ConfiguracionCorreo",
    "HistorialPagos",
    "TipoPatron",
    "AutomationAudit",
    "AutomationMetrics",
    "ConfiguracionAutomatizacion",
    "ProveedorTrust",
    "Base",
]
