# app/models/role.py
from sqlalchemy import Column, BigInteger, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class Role(Base):
    __tablename__ = "roles"
    id = Column(BigInteger, primary_key=True)
    nombre = Column(String(50))
    responsables = relationship("Responsable", back_populates="role_obj")