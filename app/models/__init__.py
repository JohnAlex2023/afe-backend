from app.db.base import Base

# Importa modelos para que se registren en Base.metadata
from .cliente import Cliente
from .proveedor import Proveedor
from .factura import Factura
from .responsable import Responsable
from .responsable_proveedor import ResponsableProveedor
from .role import Role
from .audit_log import AuditLog

__all__ = [
    "Cliente",
    "Proveedor",
    "Factura",
    "Responsable",
    "ResponsableProveedor",
    "Role",
    "AuditLog",
    "Base",
]
