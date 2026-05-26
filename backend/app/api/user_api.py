from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from uuid import UUID
from app.db.session import get_session
from app.models.user import User, UserCreate, UserUpdate
from app.core.hashing import password_hash, verify_password
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from app.core.hashing import password_hash, verify_password, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.security import get_current_user
import jwt

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login") 

@router.get("/me")
def get_me(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
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


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None

@router.put("/me")
def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if data.email and data.email != current_user.email:
        existing = session.exec(select(User).where(User.email == data.email)).first()
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email sudah digunakan oleh akun lain."
            )
        current_user.email = data.email
    
    if data.name is not None:
        current_user.name = data.name

    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
    }

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

@router.put("/me/password")
def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not verify_password(data.current_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password saat ini salah."
        )
    
    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password baru minimal 6 karakter."
        )

    current_user.password = password_hash.hash(data.new_password)
    session.add(current_user)
    session.commit()
    return {"message": "Password berhasil diubah."}

@router.post("/register", response_model=User)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    hashed_password = password_hash.hash(user.password)
    db_user = User(
        email=user.email,
        password=hashed_password,
        name=user.name
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@router.get("/{user_id}")
def get_user(user_id: UUID, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    statement = select(User).where(User.email == form_data.username)
    user = session.exec(statement).first()
    
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email atau password salah"
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + access_token_expires
    
    payload = {
        "sub": str(user.id),
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": encoded_jwt, "token_type": "bearer"}