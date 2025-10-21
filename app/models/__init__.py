from app.db.base import Base

# Importa modelos para que se registren en Base.metadata
from .proveedor import Proveedor
from .factura import Factura
from .factura_item import FacturaItem
from .responsable import Responsable
#  ELIMINADO: ResponsableProveedor (migrado a AsignacionNitResponsable)
from .role import Role
from .audit_log import AuditLog
from .workflow_aprobacion import (
    WorkflowAprobacionFactura,
    AsignacionNitResponsable,
    NotificacionWorkflow
)
from .historial_pagos import HistorialPagos, TipoPatron
from .email_config import CuentaCorreo, NitConfiguracion, HistorialExtraccion

__all__ = [
    "Proveedor",
    "Factura",
    "FacturaItem",
    "Responsable",
    #  ELIMINADO: "ResponsableProveedor",
    "Role",
    "AuditLog",
    "WorkflowAprobacionFactura",
    "AsignacionNitResponsable",
    "NotificacionWorkflow",
    "HistorialPagos",
    "TipoPatron",
    "CuentaCorreo",
    "NitConfiguracion",
    "HistorialExtraccion",
    "Base",
]
