# app/api/v1/roles.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas.role import RoleRead
from app.crud.role import list_roles
from app.core.security import get_current_responsable, require_role

router = APIRouter(prefix="/roles", tags=["roles"])

@router.get("/", response_model=List[RoleRead])
def list_all(db: Session = Depends(get_db), current_user = Depends(require_role("admin"))):
    return list_roles(db)
