# File: backend/app/api/todos.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.db.session import get_session
import app.models as models
from app.crud import todos_crud
import app.services.todo_service as todo_service
from app.models.todo import Todo, TodoUpdate, TodoCreate
from app.core.security import get_current_user
from app.models.user import User
import uuid

router = APIRouter(
    prefix="/todos",
    tags=["Todos"]
)

@router.get("/search", response_model=list[models.Todo])
def search_todos(
    q: str = Query(..., min_length=1, description="Kata kunci pencarian"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return todo_service.search_todos(q, session, current_user)

@router.post("/", response_model=Todo)
def create_todo(
    todo: TodoCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)):
    return todo_service.create_todo(todo, session, current_user)

@router.get("/", response_model=list[models.Todo])
def read_todos(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)):
    return todo_service.read_todos(session, current_user)

@router.get("/{todo_id}", response_model=models.Todo)
def read_todo(todo_id: uuid.UUID, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    return todo_service.read_todo_by_id(todo_id, session, current_user)

@router.delete("/{todo_id}")
def delete_todo(todo_id: uuid.UUID, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    return todo_service.delete_todo(todo_id, session, current_user)

@router.patch("/{todo_id}", response_model=models.Todo)
def edit_todo(
    todo_id: uuid.UUID, 
    todo: TodoUpdate, 
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    print(current_user)
    return todo_service.update_todo(todo_id, todo, session, current_user)