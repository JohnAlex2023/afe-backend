# app/main.py



from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import proveedor, factura, cliente, responsable, role
from app.core.auth import auth_router
from app.core.logging_middleware import log_requests
from app.core.error_handlers import register_error_handlers


app = FastAPI(
    title="Invoice API",
    description="API para gestión de facturas y proveedores",
    version="2.0.0"
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar a dominios específicos en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Routers principales
app.include_router(proveedor.router)
app.include_router(factura.router)
app.include_router(cliente.router)
app.include_router(responsable.router)
app.include_router(role.router)
app.include_router(auth_router)

# Middleware de logging
app.middleware("http")(log_requests)

# Registro de manejadores globales de errores
register_error_handlers(app)
