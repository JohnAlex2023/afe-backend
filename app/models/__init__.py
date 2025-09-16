# app/models/__init__.py
# importar para que Alembic vea metadata
from .factura import Factura
from .cliente import Cliente
from .proveedor import Proveedor
from .responsable import Responsable
from .role import Role
from .audit_log import AuditLog
from .responsable_proveedor import ResponsableProveedor
