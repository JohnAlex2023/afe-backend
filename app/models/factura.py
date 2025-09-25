# app/models/factura.py
from sqlalchemy import Column, BigInteger, String, Date, Numeric, Enum, Boolean, ForeignKey, DateTime, UniqueConstraint, JSON
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
    subtotal = Column(Numeric(15, 2, asdecimal=True))
    iva = Column(Numeric(15, 2, asdecimal=True))
    total = Column(Numeric(15, 2, asdecimal=True))
    moneda = Column(String(10), nullable=False, server_default="COP")
    estado = Column(Enum(EstadoFactura), default=EstadoFactura.pendiente, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)
    observaciones = Column(String(2048), nullable=True)
    cufe = Column(String(100), unique=True, nullable=False)
    total_a_pagar = Column(Numeric(15, 2, asdecimal=True))
    responsable_id = Column(BigInteger, ForeignKey("responsables.id"), nullable=True)
    aprobada_automaticamente = Column(Boolean, default=False)
    creado_por = Column(String(100), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # ✨ CAMPOS PARA AUTOMATIZACIÓN DE FACTURAS RECURRENTES ✨
    
    # Concepto y clasificación
    concepto_principal = Column(String(1000), nullable=True, 
                               comment="Concepto principal extraído del XML")
    concepto_normalizado = Column(String(200), nullable=True, index=True,
                                 comment="Concepto normalizado para matching de recurrencia")
    concepto_hash = Column(String(32), nullable=True, index=True,
                          comment="Hash MD5 del concepto normalizado")
    tipo_factura = Column(String(50), nullable=True,
                         comment="Clasificación: servicio_recurrente, compra_unica, etc")
    
    # Items y orden de compra
    items_resumen = Column(JSON, nullable=True,
                          comment="Array JSON con los 5 items principales")
    orden_compra_numero = Column(String(50), nullable=True, index=True,
                                comment="Número de orden de compra del XML")
    orden_compra_sap = Column(String(50), nullable=True,
                             comment="Número SAP de la orden de compra")
    
    # Automatización inteligente
    patron_recurrencia = Column(String(50), nullable=True,
                               comment="Patrón detectado: mensual, quincenal, semanal")
    confianza_automatica = Column(Numeric(3, 2), nullable=True,
                                 comment="Confianza (0.00-1.00) para aprobación automática")
    factura_referencia_id = Column(BigInteger, ForeignKey("facturas.id"), nullable=True,
                                  comment="ID de factura del mes anterior usada como referencia")
    motivo_decision = Column(String(500), nullable=True,
                           comment="Razón de la decisión automática")
    
    # Metadata y auditoría
    procesamiento_info = Column(JSON, nullable=True,
                              comment="Información técnica del procesamiento")
    notas_adicionales = Column(JSON, nullable=True,
                             comment="Notas adicionales extraídas del XML")
    fecha_procesamiento_auto = Column(DateTime(timezone=True), nullable=True,
                                     comment="Cuándo se ejecutó el procesamiento automático")
    version_algoritmo = Column(String(20), nullable=True, server_default="1.0",
                              comment="Versión del algoritmo de automatización")

    cliente = relationship("Cliente", back_populates="facturas", lazy="joined")
    proveedor = relationship("Proveedor", back_populates="facturas", lazy="joined")
    responsable = relationship("Responsable", back_populates="facturas", lazy="joined")
    
    # Relationship para factura de referencia (para automatización)
    factura_referencia = relationship("Factura", remote_side=[id], backref="facturas_relacionadas")
    
    __table_args__ = (UniqueConstraint("numero_factura", "proveedor_id", name="uix_num_prov"),)
