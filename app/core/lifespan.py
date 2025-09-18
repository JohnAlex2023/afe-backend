from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.db.init_db import create_default_roles_and_admin
from app.utils.logger import logger
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja startup/shutdown de la app.
    Ideal para inicializar y cerrar recursos empresariales.
    """
    try:
        # --- Startup ---
        
        if settings.environment == "development":
             Base.metadata.create_all(bind=engine)

        session = Session(bind=engine)
        try:
            create_default_roles_and_admin(session)
        finally:
            session.close()

        logger.info("Startup completado correctamente")

    except Exception as e:
        logger.exception("Error en startup: %s", e)

    # La app se levanta aquí
    yield

    # --- Shutdown ---
    logger.info("Aplicación apagándose...")
