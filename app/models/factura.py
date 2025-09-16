# app/models/factura.py
from sqlalchemy import Column, BigInteger, String, Date, Numeric, Enum, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class EstadoFactura(enum.Enum):
    pendiente = "pendiente"
    en_revision = "en_revision"
    aprobada = "aprobada"
    rechazada = "rechazada"
    aprobada_auto = "aprobada_auto"

class Factura(Base):
    __tablename__ = "facturas"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    numero_factura = Column(String(50), nullable=False)
    fecha_emision = Column(Date, nullable=False)
    cliente_id = Column(BigInteger, ForeignKey("clientes.id"), nullable=True)
    proveedor_id = Column(BigInteger, ForeignKey("proveedores.id"), nullable=True)
    subtotal = Column(Numeric(15,2))
    iva = Column(Numeric(15,2))
    total = Column(Numeric(15,2))
    moneda = Column(String(10))
    estado = Column(Enum(EstadoFactura), default=EstadoFactura.pendiente, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)
    observaciones = Column(String(2048), nullable=True)
    cufe = Column(String(100), unique=True, nullable=False)
    total_a_pagar = Column(Numeric(15,2))
    responsable_id = Column(BigInteger, ForeignKey("responsables.id"), nullable=True)
    aprobada_automaticamente = Column(Boolean, default=False)
    creado_por = Column(String(100), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    cliente = relationship("Cliente", back_populates="facturas", lazy="joined")
    proveedor = relationship("Proveedor", back_populates="facturas", lazy="joined")
    responsable = relationship("Responsable", back_populates="facturas", lazy="joined")
    __table_args__ = (UniqueConstraint("numero_factura", "proveedor_id", name="uix_num_prov"),)
