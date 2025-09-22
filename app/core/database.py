# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Base que usarán todos los modelos
Base = declarative_base()

# Motor de conexión a la BD
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True
)

# Sesión de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
