from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from typing import Dict, Any
from app.config import settings
import logging

logger = logging.getLogger("afe_backend")

auth_router = APIRouter(tags=["Auth"])

@auth_router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, Any]:
    """
    Endpoint de autenticación.
    ⚠️ Actualmente simula un login hardcodeado. 
    En producción, validar credenciales contra la base de datos.
    """
    if form_data.username == "responsable" and form_data.password == "1234":
        token_data = {"sub": "2", "role": "responsable"}
        access_token = jwt.encode(
            token_data, settings.secret_key, algorithm=settings.algorithm
        )
        logger.info("Usuario autenticado: %s", form_data.username)
        return {"access_token": access_token, "token_type": "bearer"}

    logger.warning("Intento de login fallido para usuario: %s", form_data.username)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales incorrectas",
    )
