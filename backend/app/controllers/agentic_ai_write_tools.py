from typing import Optional

from langchain_core.tools import tool
from sqlmodel import Session

from app.controllers.agentic_ai_helpers import (
    clean_optional_text,
    get_user,
    parse_deadline,
    parse_uuid,
    serialize_todo,
)
from app.db.session import engine
from app.models.todo import Todo, TodoUpdate
from app.services import todo_service


@tool
def create_todo(
    user_id: str,
    title: str,
    description: str = "",
    deadline: str = "",
    completed: Optional[bool] = None,
    is_daily: Optional[bool] = None,
    is_weekly: Optional[bool] = None,
    is_monthly: Optional[bool] = None,
    is_yearly: Optional[bool] = None,
) -> dict | str:
    """
    Buat ToDo baru untuk user aktif. Ini aman dieksekusi langsung jika title jelas.
    Deadline boleh berupa tanggal/jam natural yang sudah dinormalisasi agent.
    """
    try:
        if not title or title.strip() == "":
            return "Error: title wajib diisi untuk membuat ToDo."

        with Session(engine) as session:
            user = get_user(session, user_id)
            db_todo = Todo(
                title=title.strip(),
                description=clean_optional_text(description),
                deadline=parse_deadline(deadline),
                completed=completed if completed is not None else False,
                is_daily=is_daily if is_daily is not None else False,
                is_weekly=is_weekly if is_weekly is not None else False,
                is_monthly=is_monthly if is_monthly is not None else False,
                is_yearly=is_yearly if is_yearly is not None else False,
                user_id=user.id,
            )
            created = todo_service.create_todo(db_todo, session, current_user=user)
            return serialize_todo(created)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def update_todo(
    user_id: str,
    todo_id: str,
    title: str = "",
    description: str = "",
    deadline: str = "",
    completed: Optional[bool] = None,
) -> dict | str:
    """
    Update satu ToDo milik user. Gunakan hanya jika todo_id sudah jelas.
    Untuk update banyak todo sekaligus, buat request konfirmasi terlebih dahulu.
    """
    try:
        if not todo_id:
            return "Error: todo_id wajib diisi untuk update."

        update_data = _build_todo_update(title, description, deadline, completed)
        if not update_data:
            return "Error: tidak ada field yang perlu diupdate."

        with Session(engine) as session:
            user = get_user(session, user_id)
            updated = todo_service.update_todo(
                parse_uuid(todo_id, "todo_id"),
                TodoUpdate(**update_data),
                session,
                user,
            )
            return serialize_todo(updated)
    except Exception as exc:
        return f"Error: {exc}"


def _build_todo_update(
    title: str,
    description: str,
    deadline: str,
    completed: Optional[bool],
) -> dict:
    update_data = {}
    if title and title.strip() != "":
        update_data["title"] = title.strip()
    if description is not None and str(description).strip() != "":
        update_data["description"] = clean_optional_text(description)
    if deadline is not None and str(deadline).strip() != "":
        update_data["deadline"] = parse_deadline(deadline)
    if completed is not None:
        update_data["completed"] = completed
    return update_data
