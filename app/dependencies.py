from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt


SECRET_KEY = "tu_clave_secreta"  # Reemplaza por una clave segura
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    # Decodifica el token y obtiene el usuario y su rol
    # Aquí deberías consultar la base de datos y validar el usuario
    # Ejemplo simplificado:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        role = payload.get("role")
        # Consulta el usuario en la base de datos
        # user = db.query(Responsable).filter_by(id=user_id).first()
        # return user
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