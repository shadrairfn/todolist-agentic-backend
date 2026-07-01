from datetime import datetime
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.session import get_session
from app.models.agents import AgentMessage, AgentSession, AgentSessionCreate, AgentToolCall
from app.models.user import User
from app.services.agentic_tool_history_service import recent_tool_calls


def _ensure_session_owner(db_session: AgentSession, current_user: User):
    has_user_identity = (
        current_user
        and (
            isinstance(current_user, User)
            or type(current_user).__name__ == "User"
            or hasattr(current_user, "id")
        )
    )
    if has_user_identity and db_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke Session ini")


def create_sessions(
    data: AgentSessionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    new_session = AgentSession(
        title=data.title,
        user_id=current_user.id,
        created_at=datetime.now(),
    )

    session.add(new_session)
    session.commit()
    session.refresh(new_session)
    return new_session


def get_all_sessions(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.query(AgentSession).filter(AgentSession.user_id == current_user.id).all()


def get_session_by_id(
    session_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    db_session = session.get(AgentSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    _ensure_session_owner(db_session, current_user)
    return db_session


def update_session(
    session_id: UUID,
    title: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    db_session = get_session_by_id(session_id, session, current_user)
    db_session.title = title
    session.add(db_session)
    session.commit()
    session.refresh(db_session)
    return db_session


def delete_session_by_id(
    session_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    db_session = get_session_by_id(session_id, session, current_user)
    session.delete(db_session)
    session.commit()
    return {"message": f"Session '{db_session.title}' berhasil dihapus"}


def get_all_chat_user(
    session_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    get_session_by_id(session_id, session, current_user)
    return (
        session.query(AgentMessage)
        .filter(
            AgentMessage.session_id == session_id,
            AgentMessage.user_id == current_user.id,
        )
        .all()
    )


def delete_chat_history(
    session_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    get_session_by_id(session_id, session, current_user)

    deleted_messages = (
        session.query(AgentMessage)
        .filter(
            AgentMessage.session_id == session_id,
            AgentMessage.user_id == current_user.id,
        )
        .delete(synchronize_session=False)
    )
    deleted_tool_calls = (
        session.query(AgentToolCall)
        .filter(
            AgentToolCall.session_id == session_id,
            AgentToolCall.user_id == current_user.id,
        )
        .delete(synchronize_session=False)
    )
    session.commit()

    return {
        "message": "Riwayat chat berhasil dihapus",
        "deleted_messages": deleted_messages,
        "deleted_tool_calls": deleted_tool_calls,
    }


def recent_message(
    session_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user_messages = _recent_message_contents(session_id, session, current_user, role="user")
    agent_messages = _recent_message_contents(session_id, session, current_user, role="agent")

    response = []
    for index, user_message in enumerate(user_messages):
        agent_msg = f"{agent_messages[index]}" if index < len(agent_messages) else ""
        response.append({"user": f"{user_message}", "agent": agent_msg})
    return response


def _recent_message_contents(
    session_id: UUID,
    session: Session,
    current_user: User,
    role: str,
):
    return (
        session.query(AgentMessage.content)
        .filter(
            AgentMessage.session_id == session_id,
            AgentMessage.user_id == current_user.id,
            AgentMessage.role == role,
        )
        .order_by(AgentMessage.created_at.desc())
        .limit(5)
        .all()
    )
