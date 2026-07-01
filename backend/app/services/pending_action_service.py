from datetime import datetime, timedelta
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlmodel import Session, select

from app.core.security import get_current_user
from app.db.session import get_session
from app.models.agents import PendingAction
from app.models.user import User
from app.services.agentic_session_service import get_session_by_id


def create_pending_action(
    action_type: str,
    payload_json: dict,
    preview_json: dict,
    session_id: UUID,
    session: Session,
    current_user: User,
    expires_in_minutes: int = 10,
):
    get_session_by_id(session_id, session, current_user)
    pending_action = PendingAction(
        user_id=current_user.id,
        session_id=session_id,
        action_type=action_type,
        payload_json=payload_json,
        preview_json=preview_json,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes),
    )
    session.add(pending_action)
    session.commit()
    session.refresh(pending_action)
    return pending_action


def get_pending_actions(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    statement = select(PendingAction).where(
        PendingAction.user_id == current_user.id,
        PendingAction.status == "pending",
    ).order_by(PendingAction.created_at.desc())
    return session.exec(statement).all()


def get_pending_action_by_id(
    pending_action_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pending_action = session.get(PendingAction, pending_action_id)
    if not pending_action:
        raise HTTPException(status_code=404, detail="Pending action tidak ditemukan")
    if pending_action.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke pending action ini")
    return pending_action


def cancel_pending_action(
    pending_action_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pending_action = get_pending_action_by_id(pending_action_id, session, current_user)
    if pending_action.status != "pending":
        raise HTTPException(status_code=400, detail="Pending action sudah tidak aktif")

    pending_action.status = "cancelled"
    pending_action.cancelled_at = datetime.utcnow()
    session.add(pending_action)
    session.commit()
    session.refresh(pending_action)
    return {"message": "Aksi dibatalkan", "pending_action": pending_action}


def confirm_pending_action(*args, **kwargs):
    from app.services.pending_action_confirmation_service import confirm_pending_action as confirm

    return confirm(*args, **kwargs)
