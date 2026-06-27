from fastapi import Depends, HTTPException, Query
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


def read_todo_by_id(
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
    todo_id: UUID,
    todo: TodoUpdate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    db_todo = session.get(Todo, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="ToDo tidak ditemukan")
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        if db_todo.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke ToDo ini")

    if not isinstance(todo, Todo):
        update_data = todo.model_dump(exclude_unset=True)
        db_todo.sqlmodel_update(update_data)
    else:
        db_todo = todo

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