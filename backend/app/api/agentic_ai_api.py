from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.session import get_session
from app.models.agents import AgentSessionCreate
from app.models.user import User
import app.services.agentic_service as agentic_service
from app.services.agentic_chat_service import run_agent_chat

class ChatRequest(BaseModel):
    message: str

class SessionUpdate(BaseModel):
    title: str


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

@router.patch("/sessions/{session_id}")
def update_session(session_id: UUID, data: SessionUpdate, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.update_session(session_id, data.title, session, current_user)

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
    return run_agent_chat(request.message, session_id, session, current_user)

@router.get("/session/{session_id}/chat")
def get_chat_history(session_id: UUID, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.get_all_chat_user(session_id, session, current_user)

@router.delete("/sessions/{session_id}/chat")
def delete_chat_history(session_id: UUID, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.delete_chat_history(session_id, session, current_user)

@router.get("/pending-actions")
def get_pending_actions(session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.get_pending_actions(session, current_user)

@router.get("/pending-actions/{pending_action_id}")
def get_pending_action(pending_action_id: UUID, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.get_pending_action_by_id(pending_action_id, session, current_user)

@router.post("/pending-actions/{pending_action_id}/confirm")
def confirm_pending_action(pending_action_id: UUID, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.confirm_pending_action(pending_action_id, session, current_user)

@router.post("/pending-actions/{pending_action_id}/cancel")
def cancel_pending_action(pending_action_id: UUID, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.cancel_pending_action(pending_action_id, session, current_user)
