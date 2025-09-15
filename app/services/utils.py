# Utilidades generales para el proyecto
import logging
from contextlib import contextmanager
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("afe_backend")

@contextmanager
def get_db_session() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Error en sesión DB: %s", e)
        raise
    finally:
        db.close()
