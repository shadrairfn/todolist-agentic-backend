from datetime import datetime, timedelta
from uuid import uuid4

from app.models.agents import PendingAction
from app.models.todo import TodoUpdate
from app.models.user import UserRead


def test_user_read_has_no_password_field():
    fields = set(UserRead.model_fields.keys())
    assert "password" not in fields


def test_todo_update_supports_partial_payload():
    update = TodoUpdate(title="New title")
    assert update.model_dump(exclude_unset=True) == {"title": "New title"}


def test_pending_action_defaults_to_pending():
    pending = PendingAction(
        user_id=uuid4(),
        session_id=uuid4(),
        action_type="delete_todo",
        payload_json={"todo_id": str(uuid4())},
        preview_json={"message": "Confirm delete"},
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    assert pending.status == "pending"
