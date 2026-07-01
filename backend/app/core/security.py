import jwt
from typing import Optional
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from uuid import UUID
from app.db.session import get_session
from app.models.user import User
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login") 

def create_token(data: dict, expires_delta: Optional[timedelta] = None, type: str = "access") -> str:
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY belum dikonfigurasi.")

    to_encode = data.copy()

    if type == "access":
        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
    elif type == "refresh":
        expire = datetime.utcnow() + (
            expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAY)
        )
    to_encode.update({"exp": expire, "type": type})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_access_token(user_id: str):
    return create_token(data={"sub": user_id})

def refresh_access_token(refresh_token: str, session: Session = Depends(get_session)) -> str:
    credentials_exception = HTTPException(status_code=401, detail="Invalid refresh token")
    try:
        if not settings.SECRET_KEY:
            raise credentials_exception

        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except jwt.PyJWTError:
        raise credentials_exception

    if payload.get("type") != "refresh":
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise credentials_exception

    user = session.get(User, user_uuid)
    if not user:
        raise credentials_exception

    new_access_token = create_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        type="access",
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }

def get_current_user(
    token: str = Depends(oauth2_scheme), 
    session: Session = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau kedaluwarsa",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if not settings.SECRET_KEY:
            raise credentials_exception
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") == "access":
            user_id: str = payload.get("sub") 
            if user_id is None:
                raise credentials_exception
            user_uuid = UUID(user_id)
        else:
            raise credentials_exception
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception
        
    user = session.get(User, user_uuid)
    if user is None:
        raise credentials_exception
        
    return user 
