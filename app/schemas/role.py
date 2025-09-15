from pydantic import BaseModel

class RoleSchema(BaseModel):
    id: int
    nombre: str

    class Config:
        from_attributes = True
