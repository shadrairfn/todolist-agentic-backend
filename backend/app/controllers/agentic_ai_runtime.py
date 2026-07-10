from datetime import datetime
import json

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from sqlmodel import Session, select
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.controllers.agentic_ai_tools import TOOLS
from app.core.config import settings
from app.db.session import engine
from app.models.user import User

agent_executor = None


SYSTEM_PROMPT = (
    "Anda adalah asisten AI pengelola jadwal yang cerdas. "
    "Selalu gunakan user_id aktif saat memanggil tool. "
    "Gunakan list_todos atau search_todos untuk mencari konteks sebelum update/delete. "
    "create_todo boleh langsung dieksekusi jika instruksi jelas. "
    "update_todo hanya untuk satu ToDo yang todo_id-nya jelas. "
    "Untuk semua permintaan hapus/delete, jangan menghapus langsung; "
    "gunakan request_delete_todo_confirmation atau request_bulk_delete_todos_confirmation. "
    "Jangan gunakan request_confirmation kecuali sebagai fallback kompatibilitas. "
    "Saat membuat confirmation request, selalu kirim session_id aktif ke tool. "
    "Jika tool mengembalikan requires_confirmation=true, jelaskan preview aksi dan minta user mengonfirmasi."
    "Jika user meminta untuk dibuatkan banyak jadwal, lakukan perulangan untuk memanggil masing-masing tool yang dibutuhkan"
)


def _build_llm():
    # if settings.GOOGLE_API_KEY:
    #     return ChatGoogleGenerativeAI(
    #         model="gemini-2.5-flash",
    #         temperature=0,
    #         api_key=settings.GOOGLE_API_KEY,
    #         max_tokens=None,
    #         timeout=None,
    #         max_retries=2,
    #     )

    if settings.GROQ_API_KEY:
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            api_key=settings.GROQ_API_KEY,
            max_tokens=settings.AGENT_MAX_OUTPUT_TOKENS,
        )

    raise RuntimeError("GOOGLE_API_KEY atau GROQ_API_KEY harus dikonfigurasi untuk AI agent.")


def _get_agent_executor() -> AgentExecutor:
    global agent_executor
    if agent_executor is None:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        agent = create_tool_calling_agent(llm=_build_llm(), tools=TOOLS, prompt=prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=TOOLS,
            verbose=settings.DEBUG,
            return_intermediate_steps=True,
        )
    return agent_executor


def _fallback_user_id() -> str:
    with Session(engine) as session:
        first_user = session.exec(select(User)).first()
        if first_user:
            return str(first_user.id)
    return "00000000-0000-0000-0000-000000000000"


def _build_context_message(
    chat: str,
    user_id: str,
    session_id: str | None,
    recent_message: list,
    recent_tool_calls: list,
) -> str:
    sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    compact_recent_messages = _compact_recent_messages(recent_message)
    compact_recent_tool_calls = _compact_recent_tool_calls(recent_tool_calls)
    return f"""
    Waktu Sekarang (Today's Datetime): {sekarang}

    Current user:
    user_id = {user_id}

    Current agent session:
    session_id = {session_id}

    Recent messages:
    {compact_recent_messages}

    Recent tool calls:
    {compact_recent_tool_calls}

    Current user message:
    {chat}
    """


def _truncate_text(value, limit: int = 240) -> str:
    text = str(value or "")
    return text if len(text) <= limit else f"{text[:limit]}..."


def _compact_recent_messages(recent_message: list) -> str:
    compact = []
    for item in (recent_message or [])[: settings.AGENT_RECENT_MESSAGE_LIMIT]:
        if isinstance(item, dict):
            compact.append(
                {
                    "user": _truncate_text(item.get("user")),
                    "agent": _truncate_text(item.get("agent")),
                }
            )
        else:
            compact.append(_truncate_text(item))
    return json.dumps(compact, ensure_ascii=False, default=str)


def _compact_recent_tool_calls(recent_tool_calls: list) -> str:
    compact = []
    for item in (recent_tool_calls or [])[: settings.AGENT_RECENT_TOOL_CALL_LIMIT]:
        if not isinstance(item, dict):
            compact.append(_truncate_text(item))
            continue
        compact.append(
            {
                "tool_name": item.get("tool_name"),
                "todo_id": item.get("todo_id"),
                "title": _truncate_text(item.get("title"), 120),
                "due_at": item.get("due_at"),
                "completed": item.get("completed"),
            }
        )
    return json.dumps(compact, ensure_ascii=False, default=str)


def _extract_tool_calls(response: dict) -> list[dict]:
    tool_calls_metadata = []
    for action, observation in response.get("intermediate_steps", []):
        tool_calls_metadata.append(
            {
                "tool_name": action.tool,
                "input_json": action.tool_input,
                "output_json": observation,
            }
        )
    return tool_calls_metadata


def jalankan_agent(
    chat: str,
    user_id: str | None = None,
    session_id: str | None = None,
    recent_message: list | None = None,
    recent_tool_calls: list | None = None,
):
    """Fungsi jembatan untuk dipanggil oleh server backend."""
    user_id = user_id or _fallback_user_id()
    context_message = _build_context_message(
        chat=chat,
        user_id=user_id,
        session_id=session_id,
        recent_message=recent_message or [],
        recent_tool_calls=recent_tool_calls or [],
    )
    response = _get_agent_executor().invoke({"input": context_message})

    reply_data = response.get("output", "")
    if isinstance(reply_data, list):
        reply_text = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in reply_data
        )
    else:
        reply_text = str(reply_data)

    return {
        "reply": reply_text,
        "tool_calls": _extract_tool_calls(response),
    }
