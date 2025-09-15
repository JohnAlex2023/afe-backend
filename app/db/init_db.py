from app.db.base import Base
from app.db.session import engine

# Importa todos los modelos para que se registren en Base
from app.models.proveedor import Proveedor
from app.models.factura import Factura
from app.models.cliente import Cliente
from app.models.responsable import Responsable
from app.models.role import Role

Base.metadata.create_all(bind=engine)
print("Tablas creadas correctamente.")
