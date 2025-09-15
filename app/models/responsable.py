from sqlalchemy import Column, BigInteger, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class Responsable(Base):
    __tablename__ = "responsables"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    usuario = Column(String(100), unique=True, nullable=False)
    nombre = Column(String(150))
    email = Column(String(255), unique=True, nullable=False)
    area = Column(String(100))
    role_id = Column(BigInteger, nullable=False)

    # Relación inversa con Factura
    facturas = relationship("Factura", back_populates="responsable")
