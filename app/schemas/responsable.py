from pydantic import BaseModel
from typing import Optional

class ResponsableSchema(BaseModel):
    id: int
    usuario: str
    nombre: Optional[str]
    email: str
    area: Optional[str]
    role_id: int

    class Config:
        from_attributes = True
