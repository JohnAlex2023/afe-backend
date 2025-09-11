from app.models import Base
from app.config import engine

Base.metadata.create_all(bind=engine)
print("Tablas creadas correctamente.")