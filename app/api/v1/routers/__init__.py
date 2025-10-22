from fastapi import APIRouter

# Importa cada módulo de rutas
from app.api.v1.routers import (
    auth,
    proveedores,
    responsables,
    roles,
    facturas,
    automation,
    automatizacion,
    historial_pagos,
    workflow,
    asignacion_nit,  #   NUEVO: Reemplazo de responsable_proveedor
    flujo_automatizacion,
    email_config,
    email_health,  # Health check para servicios de email
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
api_router.include_router(proveedores.router, prefix="/proveedores", tags=["Proveedores"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(facturas.router, prefix="/facturas", tags=["Facturas"])
api_router.include_router(automation.router, prefix="/automation", tags=["Automatización"])
api_router.include_router(automatizacion.router, tags=["Automatización - Mes Anterior"])
api_router.include_router(historial_pagos.router, tags=["Historial de Pagos"])
api_router.include_router(workflow.router, tags=["Workflow Aprobación"])
api_router.include_router(asignacion_nit.router, tags=["Asignación NIT"])  #   NUEVO
api_router.include_router(flujo_automatizacion.router, tags=["Flujo de Automatización"])
api_router.include_router(email_config.router, tags=["Email Configuration"])
api_router.include_router(email_health.router, tags=["Email Health"])
