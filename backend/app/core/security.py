import jwt
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from uuid import UUID
from app.db.session import get_session
from app.models.user import User
import os
from dotenv import load_dotenv

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login") 

SECRET_KEY = os.getenv("SECRET_KEY") 
ALGORITHM = "HS256"

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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub") 
        if user_id is None:
            raise credentials_exception
        user_uuid = UUID(user_id)
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = session.get(User, user_uuid)
    if user is None:
        raise credentials_exception
        
    return user 

oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="users/login", auto_error=False)

def get_optional_current_user(
    token: str = Depends(oauth2_scheme_optional),
    session: Session = Depends(get_session)
) -> Optional[User]:
    from typing import Optional
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        user_uuid = UUID(user_id)
        return session.get(User, user_uuid)
    except Exception:
        return None