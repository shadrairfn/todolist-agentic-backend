import re
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select

from app.controllers.agentic_ai import jalankan_agent
from app.models.agents import AgentMessage, AgentToolCall, PendingAction
from app.models.user import User
from app.services.agentic_session_service import recent_message, recent_tool_calls
from app.services.pending_action_confirmation_service import confirm_pending_action as execute_pending_action
from app.services.pending_action_service import cancel_pending_action


def run_agent_chat(
    message: str,
    session_id: UUID,
    session: Session,
    current_user: User,
) -> dict:
    _save_user_message(message, session_id, session, current_user)

    greeting_reply = _simple_greeting_reply(message)
    if greeting_reply:
        _save_agent_response(greeting_reply, [], session_id, session, current_user)
        return {
            "session_id": str(session_id),
            "reply": greeting_reply,
            "tool_calls": [],
            "requires_confirmation": False,
        }

    pending_action_reply = _handle_pending_action_reply(message, session_id, session, current_user)
    if pending_action_reply:
        return {
            "session_id": str(session_id),
            **pending_action_reply,
        }

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
        "tool_calls": _compact_tool_calls_for_response(tool_calls),
        **_extract_pending_action(tool_calls),
    }


def _simple_greeting_reply(message: str) -> str | None:
    normalized = " ".join(message.lower().strip().split())
    if normalized in {
        "halo",
        "hallo",
        "hello",
        "hai",
        "hi",
        "hey",
        "pagi",
        "siang",
        "sore",
        "malam",
        "assalamualaikum",
        "assalamu alaikum",
    }:
        return "Halo! Ada yang bisa saya bantu?"
    return None


def _handle_pending_action_reply(
    message: str,
    session_id: UUID,
    session: Session,
    current_user: User,
) -> dict | None:
    intent = _pending_action_reply_intent(message)
    if not intent:
        return None

    pending_action = _latest_pending_action(session_id, session, current_user)
    if not pending_action:
        return {
            "reply": "Tidak ada aksi yang menunggu konfirmasi.",
            "tool_calls": [],
            "requires_confirmation": False,
        }

    try:
        if intent == "confirm":
            result = execute_pending_action(pending_action.id, session, current_user)
        else:
            result = cancel_pending_action(pending_action.id, session, current_user)
    except HTTPException as exc:
        return {
            "reply": str(exc.detail),
            "tool_calls": [],
            "requires_confirmation": False,
        }

    return {
        "reply": result.get("message", "Aksi berhasil diproses."),
        "tool_calls": [],
        "requires_confirmation": False,
    }


def _pending_action_reply_intent(message: str) -> str | None:
    normalized = _normalize_pending_action_reply(message)
    if not normalized:
        return None

    words = normalized.split()
    if len(words) > 3:
        return None

    if normalized in {
        "ya",
        "iya",
        "y",
        "yes",
        "ok",
        "oke",
        "setuju",
        "confirm",
        "konfirmasi",
        "lanjut",
        "lanjutkan",
        "boleh",
        "gas",
    }:
        return "confirm"

    if normalized in {
        "batal",
        "cancel",
        "tidak",
        "no",
        "jangan",
        "gak",
        "ga",
        "nggak",
        "enggak",
        "stop",
    }:
        return "cancel"

    return None


def _normalize_pending_action_reply(message: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", message.lower()).strip()
    normalized = re.sub(r"([a-z])\1{2,}", r"\1", normalized)
    return " ".join(normalized.split())


def _latest_pending_action(
    session_id: UUID,
    session: Session,
    current_user: User,
) -> PendingAction | None:
    statement = (
        select(PendingAction)
        .where(
            PendingAction.user_id == current_user.id,
            PendingAction.session_id == session_id,
            PendingAction.status == "pending",
        )
        .order_by(PendingAction.created_at.desc())
    )
    return session.exec(statement).first()


def _compact_tool_calls_for_response(tool_calls: list[dict]) -> list[dict]:
    compact = []
    for tool_call in tool_calls:
        output_json = tool_call.get("output_json")
        if isinstance(output_json, dict):
            output_summary = {
                key: output_json.get(key)
                for key in ("id", "title", "due_at", "completed", "requires_confirmation", "pending_action_id", "action_type")
                if key in output_json
            }
        elif isinstance(output_json, list):
            output_summary = {"items": len(output_json)}
        else:
            output_summary = {"result": str(output_json)[:200]}

        compact.append(
            {
                "tool_name": tool_call.get("tool_name"),
                "input_json": tool_call.get("input_json"),
                "output_json": output_summary,
            }
        )
    return compact


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
