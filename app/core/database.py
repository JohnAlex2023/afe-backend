from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.base import Base  # <- Se importa la Base aquí

# Engine de conexión
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

# Sesión de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
