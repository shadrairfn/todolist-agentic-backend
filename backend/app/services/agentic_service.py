from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.security import get_current_user
from app.models.user import User
from app.models.agents import AgentSessionCreate, AgentSession, AgentMessage, AgentToolCall
from sqlmodel import Session
from app.db.session import get_session
from datetime import datetime
from uuid import UUID

def create_sessions(
    data: AgentSessionCreate, 
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
):
    sessions = session.query(AgentSession).filter(AgentSession.user_id == current_user.id).all()
    return sessions

def get_session_by_id(
    session_id: UUID, 
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    db_session = session.get(AgentSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        if db_session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke Session ini")
    return db_session

def delete_session_by_id(
    session_id: UUID, 
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    db_session = session.get(AgentSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        if db_session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke Session ini")
    session.delete(db_session)
    session.commit()
    return {"message": f"Session '{db_session.title}' berhasil dihapus"}

def get_all_chat_user(
    session_id: UUID, 
    session: Session= Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    messages = session.query(
        AgentMessage
    ).filter(
        AgentMessage.session_id == session_id, 
        AgentMessage.user_id == current_user.id
    ).all()
    return messages
 
def recent_message(
    session_id: UUID, 
    session: Session= Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    user_messages = session.query(
        AgentMessage.content
    ).filter(
        AgentMessage.session_id == session_id, 
        AgentMessage.user_id == current_user.id, 
        AgentMessage.role == "user"
    ).order_by(AgentMessage.created_at.desc())\
    .limit(5).all()

    agent_messages = session.query(
        AgentMessage.content
    ).filter(
        AgentMessage.session_id == session_id, 
        AgentMessage.user_id == current_user.id, 
        AgentMessage.role == "agent"
    ).order_by(AgentMessage.created_at.desc())\
    .limit(5).all()
    
    response = []

    for i in range(len(user_messages)):
        response.append({
            "user": f"{user_messages[i]}",
            "agent": f"{agent_messages[i]}"
        })
    
    return response
    
def recent_tool_calls(
    session_id:UUID, 
    session: Session= Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    tool_calls = session.query(
        AgentMessage.metadata_json,
        AgentMessage.created_at
    ).filter(
        AgentMessage.session_id == session_id,
        AgentMessage.user_id == current_user.id,
        AgentMessage.role == "agent"
    ).order_by(AgentMessage.created_at.desc())\
    .limit(5).all()
    
    response = []
    for tc in tool_calls:
        metadata = tc.metadata_json or []
        # Jika metadata berupa dict tunggal (bukan list), jadikan list agar bisa di-loop
        if isinstance(metadata, dict):
            metadata = [metadata]
            
        for data in metadata:
            if not isinstance(data, dict):
                continue
                
            raw_output_json = data.get("output_json") or {}
            input_json = data.get("input_json") or {}
            
            # Pastikan input_json dict (biasanya parameter action dari agent adalah dict tunggal)
            if isinstance(input_json, list):
                input_json = input_json[0] if len(input_json) > 0 else {}
            elif not isinstance(input_json, dict):
                input_json = {}
                
            # Jika output_json berupa list, kita loop agar semuanya masuk.
            # Jika berupa dict tunggal, jadikan list berisi 1 elemen agar tetap bisa di-loop.
            output_list = raw_output_json if isinstance(raw_output_json, list) else [raw_output_json]
            
            for out_item in output_list:
                if not isinstance(out_item, dict):
                    out_item = {}
                    
                response.append({
                    "todo_id": out_item.get("id"),
                    "tool_name": data.get("tool_name"),
                    "action": input_json.get("action_method"),
                    "title": out_item.get("title"),
                    "deadline": out_item.get("deadline"),
                    "completed": out_item.get("completed"),
                    "created_at": tc.created_at
                })
    
    return response