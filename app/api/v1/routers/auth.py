# app/api/v1/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt

from app.core.database import get_db
from app.models.responsable import Responsable
from app.schemas.auth import LoginRequest, TokenResponse, UsuarioResponse

router = APIRouter()

# Configuración
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "zentria-afe-secret-key-change-in-production-2025"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/login", response_model=TokenResponse, summary="Login con usuario y contraseña")
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Endpoint de login. Retorna JWT token y datos del usuario.
    """
    print(f"🔐 Login attempt for user: {credentials.usuario}")

    # Buscar usuario en tabla responsables
    usuario = db.query(Responsable).filter(Responsable.usuario == credentials.usuario).first()

    print(f"   Usuario encontrado: {usuario is not None}")
    if usuario:
        print(f"   Usuario ID: {usuario.id}, Activo: {usuario.activo}")
        password_valid = verify_password(credentials.password, usuario.hashed_password)
        print(f"   Contraseña válida: {password_valid}")

    if not usuario or not verify_password(credentials.password, usuario.hashed_password):
        print(f"    Login failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )

    # Crear token
    access_token = create_access_token(data={"sub": usuario.usuario, "id": usuario.id})

    return TokenResponse(
        access_token=access_token,
        user=UsuarioResponse(
            id=usuario.id,
            nombre=usuario.nombre,
            email=usuario.email,
            usuario=usuario.usuario,
            area=usuario.area,
            rol=usuario.role.nombre if usuario.role else "usuario",
            activo=usuario.activo,
            created_at=usuario.creado_en
        )
    )
