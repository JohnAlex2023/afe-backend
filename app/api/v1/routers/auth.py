# app/api/v1/routers/auth.py
from typing import Optional
from datetime import datetime, timedelta
import secrets
import jwt

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.core.database import get_db
from app.models.responsable import Responsable
from app.schemas.auth import LoginRequest, TokenResponse, UsuarioResponse
from app.services.microsoft_oauth_service import microsoft_oauth_service

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
    Endpoint de login tradicional con usuario y contraseña.
    Retorna JWT token y datos del usuario.
    """
    print(f"🔐 Login attempt for user: {credentials.usuario}")

    # Buscar usuario en tabla responsables
    usuario = db.query(Responsable).filter(Responsable.usuario == credentials.usuario).first()

    print(f"   Usuario encontrado: {usuario is not None}")
    if usuario:
        print(f"   Usuario ID: {usuario.id}, Activo: {usuario.activo}")

        # Validar que el usuario use autenticación local
        if usuario.auth_provider != "local":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Este usuario debe autenticarse con {usuario.auth_provider}"
            )

        if not usuario.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario configurado para autenticación OAuth"
            )

        password_valid = verify_password(credentials.password, usuario.hashed_password)
        print(f"   Contraseña válida: {password_valid}")

    if not usuario or not verify_password(credentials.password, usuario.hashed_password):
        print("    Login failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )

    # Actualizar último login
    usuario.last_login = datetime.utcnow()
    db.commit()

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


@router.get("/microsoft/authorize", summary="Iniciar autenticación con Microsoft")
def microsoft_authorize():
    """
    Redirige al usuario a la página de login de Microsoft.
    Genera un estado aleatorio para CSRF protection.
    """
    # Generar state para CSRF protection
    state = secrets.token_urlsafe(32)

    # En producción, guardar el state en caché/sesión para validarlo después
    # Por ahora, lo incluimos en la URL

    auth_url = microsoft_oauth_service.get_authorization_url(state=state)
    return {"authorization_url": auth_url, "state": state}


@router.get("/microsoft/callback", response_model=TokenResponse, summary="Callback de Microsoft OAuth")
def microsoft_callback(
    code: str = Query(..., description="Código de autorización de Microsoft"),
    state: Optional[str] = Query(None, description="Estado para CSRF protection"),
    error: Optional[str] = Query(None, description="Error devuelto por Microsoft"),
    db: Session = Depends(get_db)
):
    """
    Endpoint de callback para recibir el código de autorización de Microsoft.
    Intercambia el código por un token y crea/actualiza el usuario.
    """
    # Validar si hay error
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error en autenticación de Microsoft: {error}"
        )

    # En producción, validar el state aquí para prevenir CSRF
    # state_valido = validar_state_en_cache(state)
    # if not state_valido:
    #     raise HTTPException(status_code=400, detail="State inválido (CSRF)")

    print(f"🔐 Microsoft OAuth callback - código recibido")

    try:
        # Intercambiar código por token
        token_result = microsoft_oauth_service.get_token_from_code(code)
        access_token = token_result.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo obtener token de acceso"
            )

        # Obtener información del usuario
        user_info = microsoft_oauth_service.get_user_info(access_token)
        print(f"   Usuario Microsoft: {user_info.get('email')}")

        # Buscar o crear usuario
        usuario = microsoft_oauth_service.find_or_create_user(db, user_info)

        if not usuario.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        # Actualizar último login
        usuario.last_login = datetime.utcnow()
        db.commit()

        # Crear token JWT para nuestra aplicación
        jwt_token = create_access_token(data={"sub": usuario.usuario, "id": usuario.id})

        print(f"   ✅ Login exitoso - Usuario ID: {usuario.id}")

        return TokenResponse(
            access_token=jwt_token,
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

    except HTTPException:
        raise
    except Exception as e:
        print(f"   ❌ Error en callback de Microsoft: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando autenticación: {str(e)}"
        )
