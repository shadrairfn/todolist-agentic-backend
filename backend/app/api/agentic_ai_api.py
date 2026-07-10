import traceback
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_session
from app.models.agents import AgentSessionCreate
from app.models.user import User
import app.services.agentic_service as agentic_service
from app.services.agentic_chat_service import run_agent_chat

class ChatRequest(BaseModel):
    message: str

class WhatsAppChatRequest(BaseModel):
    message: str
    whatsapp_number: str | None = None
    session_user_id: str | None = None

class SessionUpdate(BaseModel):
    title: str


router = APIRouter(
    prefix="/agentic",      
    tags=["Agentic"]        
)

@router.post("/sessions")
def create_agent_session(data: AgentSessionCreate, session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.create_sessions(data, session, current_user)

@router.post("/sessions/whatsapp")
def get_or_create_whatsapp_session(session: Session= Depends(get_session), current_user: User = Depends(get_current_user)):
    return agentic_service.get_or_create_whatsapp_session(session, current_user)

@router.post("/internal/whatsapp/chat")
def whatsapp_chat_endpoint(
    request: WhatsAppChatRequest,
    session: Session = Depends(get_session),
    internal_api_key: str | None = Header(default=None, alias="X-Internal-API-Key"),
):
    try:
        print(
            "[whatsapp_internal] POST /agentic/internal/whatsapp/chat "
            f"session_user_id={request.session_user_id} whatsapp_number={request.whatsapp_number}",
            flush=True,
        )

        if internal_api_key != settings.SECRET_KEY:
            print("[whatsapp_internal] rejected: invalid internal API key", flush=True)
            raise HTTPException(status_code=401, detail="Invalid internal API key")

        current_user = _resolve_whatsapp_user(
            session=session,
            session_user_id=request.session_user_id,
            whatsapp_number=request.whatsapp_number,
        )
        print(f"[whatsapp_internal] resolved user_id={current_user.id}", flush=True)

        whatsapp_session = agentic_service.get_or_create_whatsapp_session(session, current_user)
        print(f"[whatsapp_internal] using session_id={whatsapp_session.id}", flush=True)

        return run_agent_chat(request.message, whatsapp_session.id, session, current_user)
    except HTTPException:
        raise
    except Exception:
        print(
            "[whatsapp_internal] unhandled error\n"
            f"request={request.model_dump()}\n"
            f"{traceback.format_exc()}",
            flush=True,
        )
        raise

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
def chat_endpoint(
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


def _resolve_whatsapp_user(
    session: Session,
    session_user_id: str | None,
    whatsapp_number: str | None,
) -> User:
    if session_user_id:
        try:
            user = session.get(User, UUID(_clean_whatsapp_identifier(session_user_id)))
            if user:
                return user
        except ValueError:
            pass

    for number in _whatsapp_number_candidates(whatsapp_number):
        user = session.exec(select(User).where(User.whatsapp_number == number)).first()
        if user:
            return user

    raise HTTPException(
        status_code=404,
        detail="Nomor WhatsApp belum tertaut ke user aplikasi",
    )


def _clean_whatsapp_identifier(value: str) -> str:
    return value.strip().split(":")[0].split("@")[0]


def _whatsapp_number_candidates(value: str | None) -> list[str]:
    if not value:
        return []

    cleaned = _clean_whatsapp_identifier(value)
    normalized = "".join(char for char in cleaned if char.isdigit())
    candidates = [cleaned, normalized]
    if cleaned.startswith("+"):
        candidates.append(cleaned[1:])
    else:
        candidates.append(f"+{cleaned}")

    if normalized.startswith("0"):
        candidates.append(f"62{normalized[1:]}")

    return list(dict.fromkeys(candidate for candidate in candidates if candidate))
