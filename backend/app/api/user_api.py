from fastapi import Response
from fastapi import APIRouter, Depends, Cookie, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from uuid import UUID
from app.core.security import get_current_user
from app.db.session import get_session
from app.models.dto.user_dto import PasswordChangeRequest, ProfileUpdateRequest, Token
from app.models.user import User, UserCreate, UserRead
from app.services.user_service import (
    change_password,
    create_user,
    get_me,
    get_user as get_user_by_id,
    login,
    update_profile,
)
from app.core.security import refresh_access_token

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


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
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    return login(response=response, form_data=form_data, session=session)

@router.post("/refresh")
def refresh(
    refresh_token: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token tidak ditemukan di cookie")
        
    return refresh_access_token(refresh_token=refresh_token, session=session)
