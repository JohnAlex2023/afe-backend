# app/models.py
from sqlalchemy import Column, Integer, String, Date, DateTime, DECIMAL, Enum, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Proveedor(Base):
    __tablename__ = 'proveedores'
    id = Column(Integer, primary_key=True)
    nit = Column(String(20), unique=True, nullable=False)
    razon_social = Column(String(128))
    area = Column(String(50))
    contacto_email = Column(String(128))
    facturas = relationship("Factura", back_populates="proveedor")

class Responsable(Base):
    __tablename__ = 'responsables'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(128))
    email = Column(String(128))
    area = Column(String(50))
    activo = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey('roles.id'))
    role = relationship("Role")
    facturas = relationship("Factura", back_populates="responsable")
class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(32), unique=True, nullable=False)

class Factura(Base):
    __tablename__ = 'facturas'
    id = Column(Integer, primary_key=True)
    numero_factura = Column(String(50))
    cufe = Column(String(128))
    fecha_emision = Column(Date)
    fecha_vencimiento = Column(Date)
    nit_proveedor = Column(String(20))
    razon_social_proveedor = Column(String(128))
    nit_cliente = Column(String(20))
    razon_social_cliente = Column(String(128))
    subtotal = Column(DECIMAL(18,2))
    iva = Column(DECIMAL(18,2))
    total_a_pagar = Column(DECIMAL(18,2))
    terminos_pago = Column(String(20))
    estado_aprobacion = Column(Enum('pendiente','aprobada','rechazada','manual'), default='pendiente')
    fecha_aprobacion = Column(DateTime)
    responsable_id = Column(Integer, ForeignKey('responsables.id'))
    observaciones = Column(Text)
    proveedor_id = Column(Integer, ForeignKey('proveedores.id'))
    proveedor = relationship("Proveedor", back_populates="facturas")
    responsable = relationship("Responsable", back_populates="facturas")
    notificaciones = relationship("Notificacion", back_populates="factura")

class Notificacion(Base):
    __tablename__ = 'notificaciones'
    id = Column(Integer, primary_key=True)
    factura_id = Column(Integer, ForeignKey('facturas.id'))
    responsable_id = Column(Integer, ForeignKey('responsables.id'))
    tipo = Column(Enum('aprobada','pendiente','rechazada'))
    fecha_envio = Column(DateTime)
    estado = Column(Enum('enviada','vista','accionada'))
    factura = relationship("Factura", back_populates="notificaciones")
    responsable = relationship("Responsable")