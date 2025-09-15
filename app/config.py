# app/config.py

import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic_settings import BaseSettings
from pydantic import Field

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Configuración principal de la aplicación, cargada desde variables de entorno.
    """

    database_url: str = Field(..., alias="DATABASE_URL", description="URL de conexión a la base de datos")
    secret_key: str = Field(..., alias="SECRET_KEY", description="Clave secreta para JWT y seguridad")
    algorithm: str = Field("HS256", alias="ALGORITHM", description="Algoritmo de cifrado JWT")
    access_token_expire_minutes: int = Field(
        30, alias="ACCESS_TOKEN_EXPIRE_MINUTES", description="Duración en minutos de los tokens de acceso"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()

# Configuración del motor de base de datos
try:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,  # Verifica la conexión antes de usarla
        pool_size=10,
        max_overflow=20,
    )
    logger.info("Conexión a la base de datos inicializada correctamente.")
except Exception as e:
    logger.critical("Error al inicializar el motor de base de datos: %s", str(e))
    raise

# Configuración de ORM
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency de FastAPI para obtener una sesión de base de datos.
    Garantiza que la sesión se cierre al finalizar.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
