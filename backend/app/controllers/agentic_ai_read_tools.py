from langchain_core.tools import tool
from sqlmodel import Session, or_, select

from app.controllers.agentic_ai_helpers import get_user, serialize_todo
from app.db.session import engine
from app.models.todo import Todo
from app.services import todo_service


@tool
def list_todos(user_id: str) -> list[dict] | str:
    """
    Ambil semua ToDo milik user aktif. Gunakan tool ini untuk melihat daftar tugas,
    mencari konteks sebelum update/delete, atau menjawab pertanyaan tentang todo user.
    """
    try:
        with Session(engine) as session:
            user = get_user(session, user_id)
            todos = todo_service.read_todos(session, current_user=user)
            return [serialize_todo(todo) for todo in todos]
    except Exception as exc:
        return f"Error: {exc}"


@tool
def search_todos(user_id: str, query: str) -> list[dict] | str:
    """
    Cari ToDo milik user berdasarkan judul atau deskripsi. Gunakan sebelum update
    atau request delete jika user menyebut tugas secara natural tanpa UUID.
    """
    try:
        with Session(engine) as session:
            user = get_user(session, user_id)
            statement = select(Todo).where(
                Todo.user_id == user.id,
                or_(
                    Todo.title.ilike(f"%{query}%"),
                    Todo.description.ilike(f"%{query}%"),
                ),
            )
            todos = session.exec(statement).all()
            return [serialize_todo(todo) for todo in todos]
    except Exception as exc:
        return f"Error: {exc}"
