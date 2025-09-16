#models.py

from sqlalchemy import Column, BigInteger, Integer, String, Date, DECIMAL, Enum, Text, Boolean, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.orm import relationship
from app.config import Base

class Role(Base):
    __tablename__ = 'roles'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nombre = Column(String(50), unique=True, nullable=False)
    responsables = relationship("Responsable", back_populates="role")

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

class Cliente(Base):
    __tablename__ = 'clientes'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nit = Column(String(64), unique=True, nullable=False)
    razon_social = Column(String(255), nullable=False)
    contacto_email = Column(String(255))
    telefono = Column(String(50))
    direccion = Column(String(255))
    creado_en = Column(TIMESTAMP)
    facturas = relationship("Factura", back_populates="cliente")

class Responsable(Base):
    __tablename__ = 'responsables'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    usuario = Column(String(100), unique=True, nullable=False)
    nombre = Column(String(150))
    email = Column(String(255), unique=True, nullable=False)
    area = Column(String(100))
    telefono = Column(String(50))
    activo = Column(Boolean, default=True)
    last_login = Column(TIMESTAMP)
    role_id = Column(BigInteger, ForeignKey('roles.id'))
    role = relationship("Role", back_populates="responsables")
    facturas = relationship("Factura", back_populates="responsable")

class ResponsableProveedor(Base):
    __tablename__ = 'responsable_proveedor'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    responsable_id = Column(BigInteger, ForeignKey('responsables.id'), nullable=False)
    proveedor_id = Column(BigInteger, ForeignKey('proveedores.id'), nullable=False)
    activo = Column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = 'audit_log'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    entidad = Column(String(64), nullable=False)
    entidad_id = Column(BigInteger, nullable=False)
    accion = Column(String(50), nullable=False)
    usuario = Column(String(100), nullable=False)
    detalle = Column(JSON)
    creado_en = Column(TIMESTAMP)

# Puedes agregar la clase Notificacion si la necesitas