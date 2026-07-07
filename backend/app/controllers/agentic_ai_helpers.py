from datetime import date, datetime, timedelta
from uuid import UUID

from sqlmodel import Session

from app.models.agents import AgentSession, PendingAction
from app.models.todo import Todo
from app.models.user import User


def parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError):
        raise ValueError(f"Format {field_name} tidak valid: {value}")


def parse_datetime(date_str: str | None) -> datetime | None:
    if not date_str:
        return None

    date_val = str(date_str).strip()
    if date_val == "" or date_val.lower() in ("none", "null", "current_date"):
        return None

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(date_val, fmt)
        except ValueError:
            continue

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            parsed_time = datetime.strptime(date_val, fmt).time()
            return datetime.combine(date.today(), parsed_time)
        except ValueError:
            continue

    try:
        from dateutil import parser

        return parser.parse(date_val)
    except Exception:
        return None


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    if value == "" or value.lower() in ("none", "null"):
        return None
    return value


def serialize_todo(todo: Todo) -> dict:
    return {
        "id": str(todo.id),
        "title": todo.title,
        "description": todo.description,
        "start_at": str(todo.start_at) if todo.start_at else None,
        "due_at": str(todo.due_at) if todo.due_at else None,
        "completed": todo.completed,
        "is_daily": todo.is_daily,
        "is_weekly": todo.is_weekly,
        "is_monthly": todo.is_monthly,
        "is_yearly": todo.is_yearly,
    }


def get_user(session: Session, user_id: str) -> User:
    user_uuid = parse_uuid(user_id, "user_id")
    user = session.get(User, user_uuid)
    if not user:
        raise ValueError("User tidak ditemukan.")
    return user


def get_agent_session(session: Session, session_id: str, user: User) -> AgentSession:
    session_uuid = parse_uuid(session_id, "session_id")
    agent_session = session.get(AgentSession, session_uuid)
    if not agent_session:
        raise ValueError("Session agent tidak ditemukan.")
    if agent_session.user_id != user.id:
        raise ValueError("Anda tidak memiliki akses ke session agent ini.")
    return agent_session


def create_pending_action_record(
    session: Session,
    user: User,
    agent_session: AgentSession,
    action_type: str,
    payload_json: dict,
    preview_json: dict,
) -> PendingAction:
    pending_action = PendingAction(
        user_id=user.id,
        session_id=agent_session.id,
        action_type=action_type,
        payload_json=payload_json,
        preview_json=preview_json,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    session.add(pending_action)
    session.commit()
    session.refresh(pending_action)
    return pending_action
