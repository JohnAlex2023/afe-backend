# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.auth_service import login
from app.schemas.auth import Token
from app.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/token", response_model=Token)
def token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    result = login(db, form_data.username, form_data.password)
    if not result:
        logger.warning("Auth failed for username=%s ip=%s", form_data.username, request.client.host if request.client else "unknown")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": result["access_token"], "token_type": "bearer"}
