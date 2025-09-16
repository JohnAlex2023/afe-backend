# app/models/responsable.py
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Responsable(Base):
    __tablename__ = "responsables"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    usuario = Column(String(100), nullable=False, unique=True)  # login
    nombre = Column(String(150))
    email = Column(String(255), nullable=False, unique=True)
    area = Column(String(100))
    telefono = Column(String(50))
    activo = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    role_id = Column(BigInteger, ForeignKey("roles.id"), nullable=True)
    hashed_password = Column(String(255), nullable=True)  # añadido para auth

    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    role_obj = relationship("Role", lazy="joined")
    facturas = relationship("Factura", back_populates="responsable", lazy="selectin")
