# app/models/role.py
from sqlalchemy import Column, BigInteger, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nombre = Column(String(100), unique=True, nullable=False)

    # Relación inversa
    responsables = relationship("Responsable", back_populates="role", lazy="selectin")
