from langchain_core.tools import tool
from sqlmodel import Session

from app.controllers.agentic_ai_helpers import (
    create_pending_action_record,
    get_agent_session,
    get_user,
    parse_uuid,
    serialize_todo,
)
from app.db.session import engine
from app.services import todo_service


@tool
def request_delete_todo_confirmation(user_id: str, session_id: str, todo_id: str) -> dict | str:
    """
    Buat proposal konfirmasi untuk menghapus satu ToDo. Tool ini TIDAK menghapus data.
    Gunakan setiap kali user meminta delete/hapus.
    """
    try:
        with Session(engine) as session:
            user = get_user(session, user_id)
            agent_session = get_agent_session(session, session_id, user)
            todo = todo_service.read_todo_by_id(parse_uuid(todo_id, "todo_id"), session, user)
            preview_json = _delete_preview([todo], f"ToDo '{todo.title}' akan dihapus jika user mengonfirmasi.")
            pending_action = create_pending_action_record(
                session=session,
                user=user,
                agent_session=agent_session,
                action_type="delete_todo",
                payload_json={"todo_id": str(todo.id)},
                preview_json=preview_json,
            )
            return _confirmation_response(pending_action.id, "delete_todo", {"todo_id": str(todo.id)}, preview_json)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def request_bulk_delete_todos_confirmation(
    user_id: str,
    session_id: str,
    todo_ids: str,
) -> dict | str:
    """
    Buat proposal konfirmasi untuk menghapus banyak ToDo. Tool ini TIDAK menghapus data.
    Gunakan untuk request seperti 'hapus semua task selesai' atau 'hapus semua jadwal minggu ini'.
    """
    try:
        todo_id_list = _parse_todo_id_list(todo_ids)
        if isinstance(todo_id_list, str):
            return todo_id_list

        with Session(engine) as session:
            user = get_user(session, user_id)
            agent_session = get_agent_session(session, session_id, user)
            todos = [
                todo_service.read_todo_by_id(parse_uuid(todo_id, "todo_id"), session, user)
                for todo_id in todo_id_list
            ]

            preview_json = _delete_preview(todos, f"{len(todos)} ToDo akan dihapus jika user mengonfirmasi.")
            payload_json = {"todo_ids": [str(todo.id) for todo in todos]}
            pending_action = create_pending_action_record(
                session=session,
                user=user,
                agent_session=agent_session,
                action_type="bulk_delete_todos",
                payload_json=payload_json,
                preview_json=preview_json,
            )
            return _confirmation_response(pending_action.id, "bulk_delete_todos", payload_json, preview_json)
    except Exception as exc:
        return f"Error: {exc}"


def _parse_todo_id_list(todo_ids: str) -> list[str] | str:
    if not todo_ids:
        return "Error: todo_ids tidak boleh kosong."

    todo_id_list = [todo_id.strip() for todo_id in todo_ids.split(",") if todo_id.strip()]
    if not todo_id_list:
        return "Error: format todo_ids tidak valid."
    return todo_id_list


def _delete_preview(todos: list, message: str) -> dict:
    return {
        "message": message,
        "items": [serialize_todo(todo) for todo in todos],
    }


def _confirmation_response(
    pending_action_id,
    action_type: str,
    payload_json: dict,
    preview_json: dict,
) -> dict:
    return {
        "requires_confirmation": True,
        "pending_action_id": str(pending_action_id),
        "action_type": action_type,
        "payload_json": payload_json,
        "preview_json": preview_json,
    }
