from app.db.base import Base

# Importa todos los modelos para que se registren en Base.metadata
from .cliente import Cliente  # noqa
from .proveedor import Proveedor  # noqa
from .factura import Factura  # noqa
from .responsable_proveedor import ResponsableProveedor  # noqa
from .responsable import Responsable  # noqa
from .role import Role  # noqa
from .audit_log import AuditLog  # noqa
