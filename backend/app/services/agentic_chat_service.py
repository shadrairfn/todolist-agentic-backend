from datetime import datetime
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

from app.controllers.agentic_ai import jalankan_agent
from app.models.agents import AgentMessage, AgentToolCall
from app.models.user import User
from app.services.agentic_session_service import recent_message, recent_tool_calls


def run_agent_chat(
    message: str,
    session_id: UUID,
    session: Session,
    current_user: User,
) -> dict:
    _save_user_message(message, session_id, session, current_user)

    agent_result = jalankan_agent(
        message,
        user_id=str(current_user.id),
        session_id=str(session_id),
        recent_message=recent_message(session_id, session, current_user),
        recent_tool_calls=recent_tool_calls(session_id, session, current_user),
    )

    reply_text = agent_result["reply"]
    tool_calls = agent_result["tool_calls"]
    _save_agent_response(reply_text, tool_calls, session_id, session, current_user)

    return {
        "session_id": str(session_id),
        "reply": reply_text,
        "tool_calls": tool_calls,
        **_extract_pending_action(tool_calls),
    }


def _save_user_message(
    message: str,
    session_id: UUID,
    session: Session,
    current_user: User,
):
    user_message = AgentMessage(
        session_id=session_id,
        user_id=current_user.id,
        role="user",
        content=message,
        metadata_json={},
        created_at=datetime.utcnow(),
    )
    session.add(user_message)
    session.commit()
    session.refresh(user_message)


def _save_agent_response(
    reply_text: str,
    tool_calls: list[dict],
    session_id: UUID,
    session: Session,
    current_user: User,
):
    session.add(
        AgentMessage(
            session_id=session_id,
            user_id=current_user.id,
            role="agent",
            content=reply_text,
            metadata_json=jsonable_encoder(tool_calls),
            created_at=datetime.utcnow(),
        )
    )

    for tool_call in tool_calls:
        session.add(_build_tool_call_record(tool_call, session_id, current_user))

    session.commit()


def _build_tool_call_record(
    tool_call: dict,
    session_id: UUID,
    current_user: User,
) -> AgentToolCall:
    output_data = jsonable_encoder(tool_call["output_json"])
    if not isinstance(output_data, dict):
        output_data = {"result": output_data}

    return AgentToolCall(
        session_id=session_id,
        user_id=current_user.id,
        tool_name=tool_call["tool_name"],
        action="execute",
        input_json=jsonable_encoder(tool_call["input_json"]),
        output_json=output_data,
        status="success",
        created_at=datetime.utcnow(),
    )


def _extract_pending_action(tool_calls: list[dict]) -> dict:
    for tool_call in tool_calls:
        output_json = tool_call.get("output_json")
        if isinstance(output_json, dict) and output_json.get("requires_confirmation"):
            return {
                "requires_confirmation": True,
                "pending_action_id": output_json.get("pending_action_id"),
                "action_type": output_json.get("action_type"),
                "preview": output_json.get("preview_json"),
            }
    return {"requires_confirmation": False}
