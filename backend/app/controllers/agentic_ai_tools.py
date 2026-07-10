from app.controllers.agentic_ai_confirmation_tools import (
    request_confirmation,
    request_bulk_delete_todos_confirmation,
    request_delete_todo_confirmation,
)
from app.controllers.agentic_ai_read_tools import list_todos, search_todos
from app.controllers.agentic_ai_write_tools import create_todo, update_todo


TOOLS = [
    list_todos,
    search_todos,
    create_todo,
    update_todo,
    request_confirmation,
    request_delete_todo_confirmation,
    request_bulk_delete_todos_confirmation,
]

__all__ = [
    "TOOLS",
    "list_todos",
    "search_todos",
    "create_todo",
    "update_todo",
    "request_confirmation",
    "request_delete_todo_confirmation",
    "request_bulk_delete_todos_confirmation",
]
