# app/models/responsable_proveedor.py
from sqlalchemy import Column, BigInteger, Boolean, ForeignKey, UniqueConstraint
from app.db.base import Base
from sqlalchemy.sql import func
from sqlalchemy import DateTime

class ResponsableProveedor(Base):
    __tablename__ = "responsable_proveedor"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    responsable_id = Column(BigInteger, ForeignKey("responsables.id"), nullable=False)
    proveedor_id = Column(BigInteger, ForeignKey("proveedores.id"), nullable=False)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('responsable_id', 'proveedor_id', name='uix_resp_prov'),)
