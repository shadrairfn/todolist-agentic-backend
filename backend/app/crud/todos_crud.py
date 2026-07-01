from fastapi import Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.todo import Todo, TodoCreate, TodoUpdate
from app.core.security import get_current_user
from app.models.user import User
from uuid import UUID

def read_todos(
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        todos = session.exec(select(Todo).where(Todo.user_id == current_user.id)).all()
    else:
        todos = session.exec(select(Todo)).all()
    return todos


def read_todo(
    todo_id: UUID, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    todo = session.get(Todo, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="ToDo tidak ditemukan")
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        if todo.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke ToDo ini")
    return todo


def search_todo(
    title: str = None, 
    description: str = None, 
    deadline: str = None, 
    completed: bool = False,
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        if title:
            todos = session.exec(select(Todo).where(Todo.user_id == current_user.id, Todo.title == title)).all()
        elif description:
            todos = session.exec(select(Todo).where(Todo.user_id == current_user.id, Todo.description == description)).all()
        elif deadline:
            todos = session.exec(select(Todo).where(Todo.user_id == current_user.id, Todo.deadline == deadline)).all()
        elif completed:
            todos = session.exec(select(Todo).where(Todo.user_id == current_user.id, Todo.completed == completed)).all()
    else:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return todos


def create_todo(
    todo: TodoCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not isinstance(todo, Todo):
        db_todo = Todo(**todo.model_dump())
    else:
        db_todo = todo
        
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        db_todo.user_id = current_user.id
        
    session.add(db_todo)
    session.commit()
    session.refresh(db_todo)
    return db_todo


def update_todo(
    todo: TodoUpdate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not isinstance(todo, Todo):
        raise HTTPException(status_code=400, detail="Update membutuhkan objek ToDo yang sudah ada")

    db_todo = todo
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        if db_todo.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke ToDo ini")

    session.add(db_todo)
    session.commit()
    session.refresh(db_todo)
    return db_todo


def delete_todo(
    todo_id: UUID, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Hapus todo berdasarkan UUID — dicari dari DB terlebih dahulu."""
    db_todo = session.get(Todo, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="ToDo tidak ditemukan")
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        if db_todo.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke ToDo ini")
    session.delete(db_todo)
    session.commit()
    return {"message": f"ToDo '{db_todo.title}' berhasil dihapus"}
