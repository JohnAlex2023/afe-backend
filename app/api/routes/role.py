from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.role import RoleSchema
from app.crud.role import get_role, get_roles, create_role
from app.db.session import SessionLocal

router = APIRouter(prefix="/roles", tags=["roles"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[RoleSchema])
def listar_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_roles(db, skip=skip, limit=limit)

@router.get("/{role_id}", response_model=RoleSchema)
def obtener_role(role_id: int, db: Session = Depends(get_db)):
    role = get_role(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return role
