# app/models/cliente.py
from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base
from sqlalchemy.orm import relationship

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nit = Column(String(64), nullable=False, unique=True)
    razon_social = Column(String(255), nullable=False)
    contacto_email = Column(String(255))
    telefono = Column(String(50))
    direccion = Column(String(255))
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    facturas = relationship("Factura", back_populates="cliente", lazy="selectin")
