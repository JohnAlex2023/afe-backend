from fastapi import APIRouter

# Importa cada módulo de rutas
from app.api.v1.routers import (
    auth,
    clientes,
    proveedores,
    responsables,
    roles,
    facturas,
    automation,
)

# Router principal con prefijo global
api_router = APIRouter(prefix="/api/v1")

# Endpoint raíz para verificar que la API funciona
@api_router.get("/", tags=["Root"])
def read_root():
    return {"message": "Bienvenido a la API v1 de AFE Backend"}

# Registro de módulos de rutas
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(responsables.router, prefix="/responsables", tags=["Responsables"])
api_router.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])
api_router.include_router(proveedores.router, prefix="/proveedores", tags=["Proveedores"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(facturas.router, prefix="/facturas", tags=["Facturas"])
api_router.include_router(automation.router, prefix="/automation", tags=["Automatización"])
