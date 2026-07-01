from datetime import datetime

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from sqlmodel import Session, select

from app.controllers.agentic_ai_tools import TOOLS
from app.core.config import settings
from app.db.session import engine
from app.models.user import User


SYSTEM_PROMPT = (
    "Anda adalah asisten AI pengelola jadwal yang cerdas. "
    "Selalu gunakan user_id aktif saat memanggil tool. "
    "Gunakan list_todos atau search_todos untuk mencari konteks sebelum update/delete. "
    "create_todo boleh langsung dieksekusi jika instruksi jelas. "
    "update_todo hanya untuk satu ToDo yang todo_id-nya jelas. "
    "Untuk semua permintaan hapus/delete, jangan menghapus langsung; "
    "gunakan request_delete_todo_confirmation atau request_bulk_delete_todos_confirmation. "
    "Saat membuat confirmation request, selalu kirim session_id aktif ke tool. "
    "Jika tool mengembalikan requires_confirmation=true, jelaskan preview aksi dan minta user mengonfirmasi."
)


llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=settings.GROQ_API_KEY)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)
agent = create_tool_calling_agent(llm=llm, tools=TOOLS, prompt=prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=TOOLS,
    verbose=settings.DEBUG,
    return_intermediate_steps=True,
)


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
    return f"""
    Waktu Sekarang (Today's Datetime): {sekarang}

    Current user:
    user_id = {user_id}

    Current agent session:
    session_id = {session_id}

    Recent messages:
    {recent_message}

    Recent tool calls:
    {recent_tool_calls}

    Current user message:
    {chat}
    """


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
    response = agent_executor.invoke({"input": context_message})

    return {
        "reply": response["output"],
        "tool_calls": _extract_tool_calls(response),
    }
