from sqlalchemy import Column, String, Date, DECIMAL, ForeignKey, Enum, Boolean, TIMESTAMP, BigInteger
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

# Enum local para el estado de la factura
class EstadoFactura(enum.Enum):
    PENDIENTE = "pendiente"
    EN_REVISION = "en_revision"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    APROBADA_AUTO = "aprobada_auto"

class Factura(Base):
    __tablename__ = "facturas"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    numero_factura = Column(String(50), nullable=False)
    cufe = Column(String(100), nullable=False, unique=True)
    fecha_emision = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)

    cliente_id = Column(BigInteger, ForeignKey("clientes.id"))
    proveedor_id = Column(BigInteger, ForeignKey("proveedores.id"))
    responsable_id = Column(BigInteger, ForeignKey("responsables.id"), nullable=True)

    subtotal = Column(DECIMAL(15, 2), nullable=False)
    iva = Column(DECIMAL(15, 2), nullable=False)
    total = Column(DECIMAL(15, 2), nullable=True, default=0.0)  # 👈 ya no rompe
    total_a_pagar = Column(DECIMAL(15, 2), nullable=True, default=0.0)

    estado = Column(Enum(EstadoFactura), default=EstadoFactura.PENDIENTE, nullable=False)
    aprobada_automaticamente = Column(Boolean, default=False)

    creado_en = Column(TIMESTAMP, nullable=False)
    actualizado_en = Column(TIMESTAMP, nullable=False)

    cliente = relationship("Cliente", back_populates="facturas")
    proveedor = relationship("Proveedor", back_populates="facturas")
    responsable = relationship("Responsable", back_populates="facturas")
