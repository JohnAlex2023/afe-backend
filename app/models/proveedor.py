# app/models/proveedor.py
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.base import Base
from sqlalchemy.orm import relationship

class Proveedor(Base):
    __tablename__ = "proveedores"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nit = Column(String(64), nullable=False, unique=True)
    razon_social = Column(String(255), nullable=False)
    area = Column(String(100))
    contacto_email = Column(String(255))
    telefono = Column(String(50))
    direccion = Column(String(255))
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    facturas = relationship("Factura", back_populates="proveedor", lazy="selectin")
