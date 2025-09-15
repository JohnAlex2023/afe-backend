from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        role = payload.get("role")
        return {"id": user_id, "role": role}
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc

def require_admin(user = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden realizar esta acción")
    return user

def require_responsable(user = Depends(get_current_user)):
    if user["role"] != "responsable":
        raise HTTPException(status_code=403, detail="Solo responsables pueden realizar esta acción")
    return user
