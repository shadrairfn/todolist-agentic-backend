from datetime import datetime
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.session import get_session
from app.models.agents import AgentMessage, AgentToolCall, PendingAction
from app.models.user import User
from app.services.pending_action_executors import ACTION_EXECUTORS
from app.services.pending_action_service import get_pending_action_by_id


def confirm_pending_action(
    pending_action_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pending_action = get_pending_action_by_id(pending_action_id, session, current_user)
    _ensure_pending_action_active(pending_action, session)

    executor = ACTION_EXECUTORS.get(pending_action.action_type)
    if not executor:
        raise HTTPException(status_code=400, detail="Action tidak didukung")

    result, tool_status, error_message = _execute_pending_action(
        executor,
        pending_action,
        session,
        current_user,
    )
    _record_pending_action_result(
        pending_action=pending_action,
        result=result,
        tool_status=tool_status,
        error_message=error_message,
        session=session,
        current_user=current_user,
    )

    if tool_status == "failed":
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "message": "Aksi berhasil dijalankan",
        "pending_action": pending_action,
        "result": result,
    }


def _ensure_pending_action_active(pending_action: PendingAction, session: Session):
    if pending_action.status != "pending":
        raise HTTPException(status_code=400, detail="Pending action sudah tidak aktif")
    if pending_action.expires_at < datetime.utcnow():
        pending_action.status = "expired"
        session.add(pending_action)
        session.commit()
        raise HTTPException(status_code=400, detail="Pending action sudah kedaluwarsa")


def _execute_pending_action(
    executor,
    pending_action: PendingAction,
    session: Session,
    current_user: User,
):
    try:
        result = executor(pending_action.payload_json, session, current_user)
        pending_action.status = "confirmed"
        pending_action.confirmed_at = datetime.utcnow()
        return result, "success", None
    except Exception as exc:
        pending_action.status = "failed"
        return {"error": str(exc)}, "failed", str(exc)


def _record_pending_action_result(
    pending_action: PendingAction,
    result: dict,
    tool_status: str,
    error_message: str | None,
    session: Session,
    current_user: User,
):
    session.add(pending_action)
    session.add(
        AgentToolCall(
            session_id=pending_action.session_id,
            user_id=current_user.id,
            tool_name="pending_action_executor",
            action=pending_action.action_type,
            input_json=pending_action.payload_json,
            output_json=result,
            status=tool_status,
            error_message=error_message,
            created_at=datetime.utcnow(),
        )
    )
    session.add(
        AgentMessage(
            session_id=pending_action.session_id,
            user_id=current_user.id,
            role="agent",
            content=_pending_action_message(pending_action.action_type, tool_status),
            metadata_json={"pending_action_id": str(pending_action.id), "result": result},
            created_at=datetime.utcnow(),
        )
    )
    session.commit()
    session.refresh(pending_action)


def _pending_action_message(action_type: str, tool_status: str) -> str:
    if tool_status == "success":
        return f"Aksi {action_type} berhasil dijalankan."
    return f"Aksi {action_type} gagal dijalankan."
