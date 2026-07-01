from uuid import UUID

from sqlmodel import Session

from app.models.agents import AgentMessage
from app.models.user import User


def recent_tool_calls(
    session_id: UUID,
    session: Session,
    current_user: User,
):
    tool_calls = (
        session.query(AgentMessage.metadata_json, AgentMessage.created_at)
        .filter(
            AgentMessage.session_id == session_id,
            AgentMessage.user_id == current_user.id,
            AgentMessage.role == "agent",
        )
        .order_by(AgentMessage.created_at.desc())
        .limit(5)
        .all()
    )

    response = []
    for tool_call in tool_calls:
        response.extend(_normalize_tool_call_metadata(tool_call))
    return response


def _normalize_tool_call_metadata(tool_call) -> list[dict]:
    metadata = tool_call.metadata_json or []
    if isinstance(metadata, dict):
        metadata = [metadata]

    response = []
    for data in metadata:
        if not isinstance(data, dict):
            continue

        input_json = _normalize_input_json(data.get("input_json") or {})
        output_list = _normalize_output_json(data.get("output_json") or {})

        for out_item in output_list:
            response.append(
                {
                    "todo_id": out_item.get("id"),
                    "tool_name": data.get("tool_name"),
                    "action": input_json.get("action_method"),
                    "title": out_item.get("title"),
                    "deadline": out_item.get("deadline"),
                    "completed": out_item.get("completed"),
                    "created_at": tool_call.created_at,
                }
            )
    return response


def _normalize_input_json(input_json) -> dict:
    if isinstance(input_json, list):
        return input_json[0] if input_json else {}
    if isinstance(input_json, dict):
        return input_json
    return {}


def _normalize_output_json(output_json) -> list[dict]:
    output_list = output_json if isinstance(output_json, list) else [output_json]
    return [item if isinstance(item, dict) else {} for item in output_list]
