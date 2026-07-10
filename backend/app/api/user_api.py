from fastapi import Response
from fastapi import APIRouter, Depends, Cookie, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from uuid import UUID
from app.core.security import get_current_user
from app.db.session import get_session
from app.models.dto.user_dto import PasswordChangeRequest, ProfileUpdateRequest, Token
from app.models.user import User, UserCreate, UserRead, UserLogin
from app.services.user_service import (
    change_password,
    create_user,
    get_me,
    get_user as get_user_by_id,
    login,
    update_profile,
)
from app.core.security import refresh_access_token

from pydantic import BaseModel
from sqlmodel import select
import re

class LinkWhatsAppRequest(BaseModel):
    whatsapp_number: str

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

@router.post("/link-whatsapp")
def link_whatsapp(
    data: LinkWhatsAppRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    normalized_number = _normalize_whatsapp_number(data.whatsapp_number)
    if not normalized_number:
        raise HTTPException(status_code=400, detail="Nomor WhatsApp tidak valid")

    current_user.whatsapp_number = normalized_number
    try:
        session.add(current_user)
        session.commit()
        session.refresh(current_user)
        return {"status": "success", "message": "Nomor WhatsApp berhasil ditautkan"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail="Nomor WhatsApp sudah digunakan oleh akun lain")

@router.get("/internal/by-whatsapp/{number}", response_model=UserRead)
def get_user_by_whatsapp(number: str, session: Session = Depends(get_session)):
    user = None
    for candidate in _whatsapp_number_candidates(number):
        user = session.exec(select(User).where(User.whatsapp_number == candidate)).first()
        if user:
            break
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _normalize_whatsapp_number(value: str | None) -> str:
    if not value:
        return ""

    cleaned = value.strip().split(":")[0].split("@")[0]
    return re.sub(r"\D+", "", cleaned)


def _whatsapp_number_candidates(value: str | None) -> list[str]:
    normalized = _normalize_whatsapp_number(value)
    if not normalized:
        return []

    candidates = [normalized]
    if normalized.startswith("0"):
        candidates.append(f"62{normalized[1:]}")
    return list(dict.fromkeys(candidates))

@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    return get_me(current_user=current_user)

@router.put("/me", response_model=UserRead)
def update(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return update_profile(data=data, current_user=current_user, session=session)

@router.put("/me/password")
def change_password_endpoint(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return change_password(data=data, current_user=current_user, session=session)

@router.post("/register", response_model=UserRead)
def register_user(user: UserCreate, session: Session = Depends(get_session)):
    return create_user(user=user, session=session)

@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: UUID, session: Session = Depends(get_session)):
    return get_user_by_id(user_id=user_id, session=session)

@router.post("/login", response_model=Token)
def login_user(
    response: Response,
    data: UserLogin,
    session: Session = Depends(get_session),
):
    return login(response=response, data=data, session=session)

@router.post("/refresh")
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token tidak ditemukan di cookie")
        
    return refresh_access_token(refresh_token=refresh_token, session=session, response=response)
