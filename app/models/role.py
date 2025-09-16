# app/models/role.py
from sqlalchemy import Column, BigInteger, String
from app.db.base import Base

class Role(Base):
    __tablename__ = "roles"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False, unique=True)
