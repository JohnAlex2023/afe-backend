# app/services/auth_service.py
from sqlalchemy.orm import Session
from app.crud.responsable import authenticate
from app.core.security import create_access_token
from datetime import timedelta

def login(db: Session, username: str, password: str, expires_delta: timedelta = None):
    user = authenticate(db, username, password)
    if not user:
        return None
    token = create_access_token(subject=str(user.id), expires_delta=expires_delta)
    from app.schemas.responsable import ResponsableRead
    user_data = ResponsableRead.model_validate(user)
    return {"access_token": token, "token_type": "bearer", "user": user_data}
