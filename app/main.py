# app/main.py

import logging
from typing import Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from jose import jwt

from app.config import settings  # Usamos settings centralizado
from app.routes import proveedores, facturas

# -------------------------
# Configuración de Logging
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("invoice_api")


# -------------------------
# Inicialización de la app
# -------------------------
app = FastAPI(
    title="Invoice API",
    description="API para gestión de facturas y proveedores",
    version="1.0.0",
    contact={
        "name": "Equipo de Desarrollo",
        "email": "soporte@empresa.com",
    },
)


# -------------------------
# Middlewares
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ Cambiar a dominios específicos en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware para loguear cada request entrante y su tiempo de respuesta.
    """
    logger.info("➡️ Petición: %s %s", request.method, request.url)
    response = await call_next(request)
    logger.info("⬅️ Respuesta: %s %s", response.status_code, request.url)
    return response


# -------------------------
# Autenticación (ejemplo)
# -------------------------
@app.post("/token", tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, Any]:
    """
    Endpoint de autenticación.
    ⚠️ Actualmente simula un login hardcodeado. 
    En producción, validar credenciales contra la base de datos.
    """
    if form_data.username == "responsable" and form_data.password == "1234":
        token_data = {"sub": "2", "role": "responsable"}
        access_token = jwt.encode(
            token_data, settings.secret_key, algorithm=settings.algorithm
        )
        logger.info("Usuario autenticado: %s", form_data.username)
        return {"access_token": access_token, "token_type": "bearer"}

    logger.warning("Intento de login fallido para usuario: %s", form_data.username)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales incorrectas",
    )


# -------------------------
# Routers
# -------------------------
app.include_router(proveedores.router, prefix="/proveedores", tags=["Proveedores"])
app.include_router(facturas.router, prefix="/facturas", tags=["Facturas"])


# -------------------------
# Manejo global de errores
# -------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error("Error HTTP %s en %s - %s", exc.status_code, request.url, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error("Error de validación en %s - %s", request.url, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )
