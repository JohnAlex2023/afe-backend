from sqlalchemy import Column, BigInteger, String, TIMESTAMP
from sqlalchemy.orm import relationship
from app.db.base import Base

class Proveedor(Base):
    __tablename__ = 'proveedores'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nit = Column(String(64), unique=True, nullable=False)
    razon_social = Column(String(255), nullable=False)
    area = Column(String(100))
    contacto_email = Column(String(255))
    telefono = Column(String(50))
    direccion = Column(String(255))
    creado_en = Column(TIMESTAMP)
    facturas = relationship("Factura", back_populates="proveedor")
