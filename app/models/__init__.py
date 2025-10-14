from app.db.base import Base

# Importa modelos para que se registren en Base.metadata
from .cliente import Cliente
from .proveedor import Proveedor
from .factura import Factura
from .factura_item import FacturaItem
from .responsable import Responsable
from .responsable_proveedor import ResponsableProveedor
from .role import Role
from .audit_log import AuditLog
from .workflow_aprobacion import (
    WorkflowAprobacionFactura,
    AsignacionNitResponsable,
    NotificacionWorkflow,
    ConfiguracionCorreo
)
from .historial_pagos import HistorialPagos, TipoPatron
from .email_config import CuentaCorreo, NitConfiguracion, HistorialExtraccion

__all__ = [
    "Cliente",
    "Proveedor",
    "Factura",
    "FacturaItem",
    "Responsable",
    "ResponsableProveedor",
    "Role",
    "AuditLog",
    "WorkflowAprobacionFactura",
    "AsignacionNitResponsable",
    "NotificacionWorkflow",
    "ConfiguracionCorreo",
    "HistorialPagos",
    "TipoPatron",
    "CuentaCorreo",
    "NitConfiguracion",
    "HistorialExtraccion",
    "Base",
]
