from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.todo import LabelCreate, LabelRead, LabelUpdate, TodoRead
from app.services import todo_service

router = APIRouter(prefix="/labels", tags=["Labels"])


@router.post("/", response_model=LabelRead)
def create_label(
    label: LabelCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.create_label(label, session, current_user)


@router.get("/", response_model=list[LabelRead])
def list_labels(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.list_labels(session, current_user)


@router.get("/{label_id}", response_model=LabelRead)
def read_label(
    label_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.read_label(label_id, session, current_user)


@router.patch("/{label_id}", response_model=LabelRead)
def update_label(
    label_id: UUID,
    label: LabelUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.update_label(label_id, label, session, current_user)


@router.delete("/{label_id}")
def delete_label(
    label_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.delete_label(label_id, session, current_user)


@router.get("/{label_id}/todos", response_model=list[TodoRead])
def list_todos_by_label(
    label_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.filter_todos(session=session, current_user=current_user, label_id=label_id)
