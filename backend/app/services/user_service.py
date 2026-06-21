from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from uuid import UUID
from fastapi import Response
from app.core.config import settings
from app.core.hashing import get_password_hash, verify_password
from app.core.security import create_token, get_current_user
from app.db.session import get_session
from app.models.dto.user_dto import PasswordChangeRequest, ProfileUpdateRequest
from app.models.user import User, UserCreate, UserRead

def create_user(user: UserCreate, session: Session = Depends(get_session)) -> User:
    existing_user = session.exec(select(User).where(User.email == user.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah digunakan.",
        )

    db_user = User(
        email=user.email,
        password=get_password_hash(user.password),
        name=user.name,
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    statement = select(User).where(User.email == form_data.username)
    db_user = session.exec(statement).first()

    if not db_user or not verify_password(form_data.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email atau password salah",
        )
 
    access_token = create_token(data={"sub": str(db_user.id)})
    refresh_token = create_token(data={"sub": str(db_user.id)}, type="refresh")
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAY * 24 * 60 * 60, # Konversi hari ke detik
        path="/"
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return {"access_token": access_token, "token_type": "bearer"}

def get_user(user_id: UUID, session: Session = Depends(get_session)):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return db_user


def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return current_user


def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if data.email and data.email != current_user.email:
        existing = session.exec(select(User).where(User.email == data.email)).first()
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email sudah digunakan oleh akun lain.",
            )
        current_user.email = data.email

    if data.name is not None:
        current_user.name = data.name

    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if not verify_password(data.current_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password saat ini salah.",
        )

    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password baru minimal 6 karakter.",
        )

    current_user.password = get_password_hash(data.new_password)
    session.add(current_user)
    session.commit()
    return {"message": "Password berhasil diubah."}
