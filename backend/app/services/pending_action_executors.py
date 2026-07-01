from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session

from app.models.todo import Todo
from app.models.user import User
from app.services import todo_service


def execute_delete_todo(payload: dict, session: Session, current_user: User):
    todo_id = UUID(payload["todo_id"])
    return todo_service.delete_todo(todo_id, session, current_user)


def execute_bulk_delete_todos(payload: dict, session: Session, current_user: User):
    todo_ids = payload.get("todo_ids") or []
    deleted = []
    for raw_todo_id in todo_ids:
        todo_id = UUID(raw_todo_id)
        todo = session.get(Todo, todo_id)
        if not todo:
            raise HTTPException(status_code=404, detail=f"ToDo {todo_id} tidak ditemukan")
        if todo.user_id != current_user.id:
            raise HTTPException(status_code=403, detail=f"Anda tidak memiliki akses ke ToDo {todo_id}")
        deleted.append({"id": str(todo.id), "title": todo.title})
        session.delete(todo)
    session.commit()
    return {"message": f"{len(deleted)} ToDo berhasil dihapus", "deleted_count": len(deleted), "deleted": deleted}


ACTION_EXECUTORS = {
    "delete_todo": execute_delete_todo,
    "bulk_delete_todos": execute_bulk_delete_todos,
}
