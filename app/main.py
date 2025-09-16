# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import auth, responsables, clientes, proveedores, roles, facturas
from app.db.base import Base
from app.db.session import engine
from app.db.init_db import create_default_roles_and_admin
from app.utils.logger import logger

def create_app() -> FastAPI:
    app = FastAPI(title="AFE Backend", version="1.0.0")
    # CORS
    origins = []
    if settings.backend_cors_origins:
        if isinstance(settings.backend_cors_origins, str):
                origins = [o.strip() for o in settings.backend_cors_origins.split(",") if o.strip()]
        else:
            origins = list(settings.backend_cors_origins)
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"], allow_credentials=True)

    # routers
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(responsables.router, prefix="/api/v1")
    app.include_router(clientes.router, prefix="/api/v1")
    app.include_router(proveedores.router, prefix="/api/v1")
    app.include_router(roles.router, prefix="/api/v1")
    app.include_router(facturas.router, prefix="/api/v1")

    @app.on_event("startup")
    def on_startup():
        try:
            # En desarrollo: crear tablas si no existen (en prod usar Alembic)
            Base.metadata.create_all(bind=engine)
            # seeds
            from sqlalchemy.orm import Session
            session = Session(bind=engine)
            try:
                create_default_roles_and_admin(session)
            finally:
                session.close()
            logger.info("Startup tasks completed")
        except Exception as e:
            logger.exception("Startup error: %s", e)
    return app

app = create_app()
