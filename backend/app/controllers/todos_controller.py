from fastapi import Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_session
import app.models as models
from app.models.todo import TodoUpdate, Todo
import app.services.todo_service as todo_service
import uuid

def read_todos(session: Session = Depends(get_session)):
    todos = session.exec(select(Todo)).all()
    return todos

def read_todo(todo_id: int, session: Session = Depends(get_session)):
    todo = session.get(Todo, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="ToDo tidak ditemukan")
    return todo 

def delete_todo(todo_id: int, session: Session = Depends(get_session)):
    todo = session.get(models.Todo, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="ToDo tidak ditemukan")
    session.delete(todo)
    session.commit()
    return {"message": "ToDo berhasil dihapus"}

def edit_todo(todo_id: uuid.UUID, todo_update: TodoUpdate, session: Session, current_user: models.User = None):
    db_todo = session.get(Todo, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="ToDo tidak ditemukan")

    update_data = todo_update.model_dump(exclude_unset=True)
    db_todo.sqlmodel_update(update_data)
    
    return todo_service.update_todo(db_todo, session, current_user)

def toggle_todo(todo_id: int, completed: bool, session: Session = Depends(get_session)):
    todo = session.get(models.Todo, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="ToDo tidak ditemukan")
    todo.completed = completed
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo