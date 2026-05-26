# File: backend/app/api/todos.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.db.session import get_session
import app.models as models
from app.crud import todos_crud
from app.controllers import todos_controller
from app.models.todo import Todo, TodoUpdate, TodoCreate
from app.core.security import get_current_user
from app.models.user import User
import uuid

# 1. Inisialisasi APIRouter
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
    """Mencari todo berdasarkan title atau description yang mengandung kata kunci."""
    statement = select(Todo).where(
        Todo.user_id == current_user.id,
        (
            Todo.title.ilike(f"%{q}%") |
            Todo.description.ilike(f"%{q}%")
        )
    )
    results = session.exec(statement).all()
    return results

@router.post("/", response_model=Todo)
def create_todo(
    todo: TodoCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)):
    return todos_crud.create_todo(todo, session, current_user)

@router.get("/", response_model=list[models.Todo])
def read_todos(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)):
    return todos_crud.read_todos(session, current_user)

@router.get("/{todo_id}", response_model=models.Todo)
def read_todo(todo_id: uuid.UUID, session: Session = Depends(get_session)):
    return todos_crud.read_todo(todo_id, session)

@router.delete("/{todo_id}")
def delete_todo(todo_id: uuid.UUID, session: Session = Depends(get_session)):
    return todos_crud.delete_todo(todo_id, session)

@router.patch("/{todo_id}", response_model=models.Todo)
def edit_todo(
    todo_id: uuid.UUID, 
    todo: TodoUpdate, 
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    return todos_controller.edit_todo(todo_id, todo, session, current_user)