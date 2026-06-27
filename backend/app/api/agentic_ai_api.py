from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.controllers.agentic_ai import jalankan_agent
from app.core.security import get_current_user
from app.models.user import User
from app.models.agents import AgentSessionCreate, AgentSession
from sqlmodel import Session
from app.db.session import get_session
from datetime import datetime
import app.services.agentic_service as agentic_service
from uuid import UUID
from app.models.agents import AgentMessage

class ChatRequest(BaseModel):
    message: str

router = APIRouter(
    prefix="/agentic",      
    tags=["Agentic"]        
)

@router.post("/sessions")
def create_agent_session(data: AgentSessionCreate, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.create_sessions(data, session, current_user)

@router.get("/sessions")
def get_sessions(session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.get_all_sessions(session, current_user)

@router.get("/sessions/{session_id}")
def read_session(session_id: UUID, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.get_session_by_id(session_id, session, current_user)

@router.delete("/sessions/{session_id}")
def delete_session(session_id: UUID, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.delete_session_by_id(session_id, session, current_user)

@router.get("/sessions/{session_id}/message")
def get_recent_message(session_id: UUID, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.recent_message(session_id, session, current_user)

@router.get("/sessions/{session_id}/toolcalls")
def get_recent_tool_calls(session_id: UUID, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.recent_tool_calls(session_id, session, current_user)

@router.post("/sessions/{session_id}/chat")
async def chat_endpoint(
    request: ChatRequest,
    session_id: UUID, 
    session: Session= Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    user_message = AgentMessage(
        session_id=session_id,
        user_id=str(current_user.id),
        role="user",
        content=request.message,
        metadata_json={},
        created_at=datetime.utcnow()
    )

    session.add(user_message)
    session.commit()
    session.refresh(user_message)

    recent_messages = agentic_service.recent_message(session_id, session, current_user)
    recent_tool_calls = agentic_service.recent_tool_calls(session_id, session, current_user)

    hasil_agent = jalankan_agent(request.message, user_id=str(current_user.id), recent_message=recent_messages, recent_tool_calls=recent_tool_calls)
    reply_text = hasil_agent["reply"]
    tool_calls = hasil_agent["tool_calls"]

    from app.models.agents import AgentToolCall
    from fastapi.encoders import jsonable_encoder

    # Simpan balasan dari AI ke tabel AgentMessage
    agent_message = AgentMessage(
        session_id=session_id,
        user_id=str(current_user.id),
        role="agent",
        content=reply_text,
        metadata_json=jsonable_encoder(tool_calls),
        created_at=datetime.utcnow()
    )
    session.add(agent_message)

    for tc in tool_calls:
        # output_json harus JSON serializable
        output_data = jsonable_encoder(tc["output_json"])
        if not isinstance(output_data, dict):
            output_data = {"result": output_data}
            
        db_tool_call = AgentToolCall(
            session_id=session_id,
            user_id=str(current_user.id),
            tool_name=tc["tool_name"],
            action="execute",
            input_json=jsonable_encoder(tc["input_json"]),
            output_json=output_data,
            status="success",
            created_at=datetime.utcnow()
        )
        session.add(db_tool_call)

    session.commit()

    return {
        "reply": reply_text,
        "tool_calls": tool_calls
    }

@router.get("/session/{session_id}/chat")
def get_chat_history(session_id: UUID, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.get_all_chat_user(session_id, session, current_user)