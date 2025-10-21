from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class ResponsableBase(BaseModel):
    usuario: str = Field(..., example="juan.perez@empresa.com")
    email: EmailStr
    nombre: Optional[str]
    role_id: Optional[int]


class ResponsableCreate(ResponsableBase):
    password: str = Field(..., min_length=8)
    area: Optional[str] = None
    telefono: Optional[str] = None


class RoleRead(BaseModel):
    id: int
    nombre: str

    class Config:
        from_attributes = True


class ResponsableRead(ResponsableBase):
    id: int
    activo: bool
    must_change_password: bool
    last_login: Optional[datetime]
    creado_en: datetime
    area: Optional[str]
    telefono: Optional[str]
    role: Optional[RoleRead] = None

    class Config:
        from_attributes = True


class ResponsableLogin(BaseModel):
    usuario: str
    password: str


class ResponsableUpdate(BaseModel):
    usuario: Optional[str] = None
    email: Optional[EmailStr] = None
    nombre: Optional[str] = None
    area: Optional[str] = None
    telefono: Optional[str] = None
    activo: Optional[bool] = None
    role_id: Optional[int] = None
    password: Optional[str] = Field(None, min_length=8)


#  DEPRECATED: Estas clases no se usan - ver AsignacionNitCreate en workflow_aprobacion.py
# Schema para asignar proveedores a un responsable
# NOTA: Mantener temporalmente para compatibilidad, pero usar AsignacionNitCreate
from typing import List

class ResponsableProveedorAssign(BaseModel):
    """DEPRECATED: Usar AsignacionNitCreate de schemas.workflow_aprobacion"""
    responsable_id: int
    nits_proveedores: List[str] = Field(..., example=["890929073", "901261003"])


# Nuevo schema para PUT (solo lista de NITs)
class ResponsableProveedorUpdate(BaseModel):
    """DEPRECATED: Usar AsignacionNitUpdate de schemas.workflow_aprobacion"""
    nits_proveedores: List[str] = Field(..., example=["890929073", "901261003"])
