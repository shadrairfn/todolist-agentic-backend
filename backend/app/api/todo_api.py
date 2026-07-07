from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.session import get_session
from app.models.todo import TodoCreate, TodoPriority, TodoStatus, TodoUpdate
from app.models.user import User
from app.schemas.todo import ChecklistItemCreate, ChecklistItemRead, ChecklistItemUpdate, TodoRead
from app.services import todo_service

router = APIRouter(prefix="/todos", tags=["Todos"])


@router.get("/search", response_model=list[TodoRead])
def search_todos(
    q: str = Query(..., min_length=1, description="Kata kunci pencarian"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.search_todos(q, session, current_user)


@router.get("/overdue", response_model=list[TodoRead])
def overdue_todos(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.filter_todos(session=session, current_user=current_user, overdue=True)


@router.get("/due-today", response_model=list[TodoRead])
def due_today_todos(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.filter_todos(session=session, current_user=current_user, due_today=True)


@router.post("/", response_model=TodoRead)
def create_todo(
    todo: TodoCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.create_todo(todo, session, current_user)


@router.get("/", response_model=list[TodoRead])
def read_todos(
    q: Optional[str] = Query(default=None, min_length=1),
    project_id: Optional[UUID] = None,
    label_id: Optional[UUID] = None,
    status: Optional[TodoStatus] = None,
    priority: Optional[TodoPriority] = None,
    overdue: bool = False,
    due_today: bool = False,
    due_this_week: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.filter_todos(
        session=session,
        current_user=current_user,
        q=q,
        project_id=project_id,
        label_id=label_id,
        status=status,
        priority=priority,
        overdue=overdue,
        due_today=due_today,
        due_this_week=due_this_week,
    )


@router.get("/by-label/{label_id}", response_model=list[TodoRead])
def read_todos_by_label(
    label_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.filter_todos(session=session, current_user=current_user, label_id=label_id)


@router.get("/{todo_id}", response_model=TodoRead)
def read_todo(
    todo_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.read_todo_by_id(todo_id, session, current_user)


@router.delete("/{todo_id}")
def delete_todo(
    todo_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.delete_todo(todo_id, session, current_user)


@router.patch("/{todo_id}", response_model=TodoRead)
def edit_todo(
    todo_id: UUID,
    todo: TodoUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.update_todo(todo_id, todo, session, current_user)


@router.post("/{todo_id}/labels/{label_id}", response_model=TodoRead)
def attach_label(
    todo_id: UUID,
    label_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.attach_label(todo_id, label_id, session, current_user)


@router.delete("/{todo_id}/labels/{label_id}", response_model=TodoRead)
def detach_label(
    todo_id: UUID,
    label_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.detach_label(todo_id, label_id, session, current_user)


@router.post("/{todo_id}/checklist", response_model=ChecklistItemRead)
def create_checklist_item(
    todo_id: UUID,
    item: ChecklistItemCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.create_checklist_item(todo_id, item, session, current_user)


@router.get("/{todo_id}/checklist", response_model=list[ChecklistItemRead])
def list_checklist_items(
    todo_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.list_checklist_items(todo_id, session, current_user)


@router.patch("/{todo_id}/checklist/{item_id}", response_model=ChecklistItemRead)
def update_checklist_item(
    todo_id: UUID,
    item_id: UUID,
    item: ChecklistItemUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.update_checklist_item(todo_id, item_id, item, session, current_user)


@router.delete("/{todo_id}/checklist/{item_id}")
def delete_checklist_item(
    todo_id: UUID,
    item_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.delete_checklist_item(todo_id, item_id, session, current_user)


@router.get("/{todo_id}/checklist-progress")
def get_checklist_progress(
    todo_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.checklist_progress(todo_id, session, current_user)
