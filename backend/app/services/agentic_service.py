from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.controllers.agentic_ai import jalankan_agent
from app.core.security import get_current_user
from app.models.user import User
from app.models.agents import AgentSessionCreate, AgentSession, AgentMessage
from sqlmodel import Session
from app.db.session import get_session
from datetime import datetime
from uuid import UUID

def create_sessions(data: AgentSessionCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    new_session = AgentSession(
        title=data.title,
        user_id=current_user.id,
        created_at=datetime.now(),
    )

    session.add(new_session)
    session.commit()
    session.refresh(new_session)
    return new_session

def get_all_sessions(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    sessions = session.query(AgentSession).filter(AgentSession.user_id == current_user.id).all()
    return sessions

def get_session_by_id(session_id: UUID, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    db_session = session.get(AgentSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        if db_session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke Session ini")
    return db_session

def delete_session_by_id(session_id: UUID, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    db_session = session.get(AgentSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        if db_session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke Session ini")
    session.delete(db_session)
    session.commit()
    return {"message": f"Session '{db_session.title}' berhasil dihapus"}

def get_all_chat_user(session_id: UUID, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    messages = session.query(AgentMessage).filter(AgentMessage.session_id == session_id, AgentMessage.user_id == current_user.id).all()
    return messages
    