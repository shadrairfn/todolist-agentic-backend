from datetime import date, datetime
from typing import Optional
from uuid import UUID

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from sqlmodel import Session, or_, select

from app.core.config import settings
from app.db.session import engine
from app.models.agents import AgentSession, PendingAction
from app.models.todo import Todo, TodoUpdate
from app.models.user import User
from app.services import todo_service

def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError):
        raise ValueError(f"Format {field_name} tidak valid: {value}")


def _parse_deadline(deadline: str | None) -> datetime | None:
    if not deadline:
        return None

    deadline_str = str(deadline).strip()
    if deadline_str == "" or deadline_str.lower() in ("none", "null", "current_date"):
        return None

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(deadline_str, fmt)
        except ValueError:
            continue

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            parsed_time = datetime.strptime(deadline_str, fmt).time()
            return datetime.combine(date.today(), parsed_time)
        except ValueError:
            continue

    try:
        from dateutil import parser

        return parser.parse(deadline_str)
    except Exception:
        return None


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    if value == "" or value.lower() in ("none", "null"):
        return None
    return value


def _serialize_todo(todo: Todo) -> dict:
    return {
        "id": str(todo.id),
        "title": todo.title,
        "description": todo.description,
        "deadline": str(todo.deadline) if todo.deadline else None,
        "completed": todo.completed,
        "is_daily": todo.is_daily,
        "is_weekly": todo.is_weekly,
        "is_monthly": todo.is_monthly,
        "is_yearly": todo.is_yearly,
    }


def _get_user(session: Session, user_id: str) -> User:
    user_uuid = _parse_uuid(user_id, "user_id")
    user = session.get(User, user_uuid)
    if not user:
        raise ValueError("User tidak ditemukan.")
    return user


def _get_agent_session(session: Session, session_id: str, user: User) -> AgentSession:
    session_uuid = _parse_uuid(session_id, "session_id")
    agent_session = session.get(AgentSession, session_uuid)
    if not agent_session:
        raise ValueError("Session agent tidak ditemukan.")
    if agent_session.user_id != user.id:
        raise ValueError("Anda tidak memiliki akses ke session agent ini.")
    return agent_session


def _create_pending_action(
    session: Session,
    user: User,
    agent_session: AgentSession,
    action_type: str,
    payload_json: dict,
    preview_json: dict,
) -> PendingAction:
    from datetime import timedelta

    pending_action = PendingAction(
        user_id=user.id,
        session_id=agent_session.id,
        action_type=action_type,
        payload_json=payload_json,
        preview_json=preview_json,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    session.add(pending_action)
    session.commit()
    session.refresh(pending_action)
    return pending_action


@tool
def list_todos(user_id: str) -> list[dict] | str:
    """
    Ambil semua ToDo milik user aktif. Gunakan tool ini untuk melihat daftar tugas,
    mencari konteks sebelum update/delete, atau menjawab pertanyaan tentang todo user.
    """
    try:
        with Session(engine) as session:
            user = _get_user(session, user_id)
            todos = todo_service.read_todos(session, current_user=user)
            return [_serialize_todo(todo) for todo in todos]
    except Exception as exc:
        return f"Error: {exc}"


@tool
def search_todos(user_id: str, query: str) -> list[dict] | str:
    """
    Cari ToDo milik user berdasarkan judul atau deskripsi. Gunakan sebelum update
    atau request delete jika user menyebut tugas secara natural tanpa UUID.
    """
    try:
        with Session(engine) as session:
            user = _get_user(session, user_id)
            statement = select(Todo).where(
                Todo.user_id == user.id,
                or_(
                    Todo.title.ilike(f"%{query}%"),
                    Todo.description.ilike(f"%{query}%"),
                ),
            )
            todos = session.exec(statement).all()
            return [_serialize_todo(todo) for todo in todos]
    except Exception as exc:
        return f"Error: {exc}"


@tool
def create_todo(
    user_id: str,
    title: str,
    description: str = "",
    deadline: str = "",
    completed: Optional[bool] = None,
    is_daily: Optional[bool] = None,
    is_weekly: Optional[bool] = None,
    is_monthly: Optional[bool] = None,
    is_yearly: Optional[bool] = None,
) -> dict | str:
    """
    Buat ToDo baru untuk user aktif. Ini aman dieksekusi langsung jika title jelas.
    Deadline boleh berupa tanggal/jam natural yang sudah dinormalisasi agent.
    """
    try:
        if not title or title.strip() == "":
            return "Error: title wajib diisi untuk membuat ToDo."

        with Session(engine) as session:
            user = _get_user(session, user_id)
            db_todo = Todo(
                title=title.strip(),
                description=_clean_optional_text(description),
                deadline=_parse_deadline(deadline),
                completed=completed if completed is not None else False,
                is_daily=is_daily if is_daily is not None else False,
                is_weekly=is_weekly if is_weekly is not None else False,
                is_monthly=is_monthly if is_monthly is not None else False,
                is_yearly=is_yearly if is_yearly is not None else False,
                user_id=user.id,
            )
            created = todo_service.create_todo(db_todo, session, current_user=user)
            return _serialize_todo(created)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def update_todo(
    user_id: str,
    todo_id: str,
    title: str = "",
    description: str = "",
    deadline: str = "",
    completed: Optional[bool] = None,
) -> dict | str:
    """
    Update satu ToDo milik user. Gunakan hanya jika todo_id sudah jelas.
    Untuk update banyak todo sekaligus, buat request konfirmasi terlebih dahulu.
    """
    try:
        if not todo_id:
            return "Error: todo_id wajib diisi untuk update."

        update_data = {}
        if title and title.strip() != "":
            update_data["title"] = title.strip()
        if description is not None and str(description).strip() != "":
            update_data["description"] = _clean_optional_text(description)
        if deadline is not None and str(deadline).strip() != "":
            update_data["deadline"] = _parse_deadline(deadline)
        if completed is not None:
            update_data["completed"] = completed

        if not update_data:
            return "Error: tidak ada field yang perlu diupdate."

        with Session(engine) as session:
            user = _get_user(session, user_id)
            updated = todo_service.update_todo(
                _parse_uuid(todo_id, "todo_id"),
                TodoUpdate(**update_data),
                session,
                user,
            )
            return _serialize_todo(updated)
    except Exception as exc:
        return f"Error: {exc}"


@tool
def request_delete_todo_confirmation(user_id: str, session_id: str, todo_id: str) -> dict | str:
    """
    Buat proposal konfirmasi untuk menghapus satu ToDo. Tool ini TIDAK menghapus data.
    Gunakan setiap kali user meminta delete/hapus.
    """
    try:
        with Session(engine) as session:
            user = _get_user(session, user_id)
            agent_session = _get_agent_session(session, session_id, user)
            todo = todo_service.read_todo_by_id(_parse_uuid(todo_id, "todo_id"), session, user)
            preview_json = {
                "message": f"ToDo '{todo.title}' akan dihapus jika user mengonfirmasi.",
                "items": [_serialize_todo(todo)],
            }
            pending_action = _create_pending_action(
                session=session,
                user=user,
                agent_session=agent_session,
                action_type="delete_todo",
                payload_json={"todo_id": str(todo.id)},
                preview_json=preview_json,
            )
            return {
                "requires_confirmation": True,
                "pending_action_id": str(pending_action.id),
                "action_type": "delete_todo",
                "payload_json": {"todo_id": str(todo.id)},
                "preview_json": preview_json,
            }
    except Exception as exc:
        return f"Error: {exc}"


@tool
def request_bulk_delete_todos_confirmation(user_id: str, session_id: str, todo_ids: str) -> dict | str:
    """
    Buat proposal konfirmasi untuk menghapus banyak ToDo. Tool ini TIDAK menghapus data.
    Gunakan untuk request seperti 'hapus semua task selesai' atau 'hapus semua jadwal minggu ini'.
    
    Args:
        user_id (str): ID user aktif.
        todo_ids (str): String berisi daftar ID ToDo yang dipisahkan dengan koma (contoh: "id1,id2").
    """
    try:
        if not todo_ids:
            return "Error: todo_ids tidak boleh kosong."
            
        todo_id_list = [t.strip() for t in todo_ids.split(",") if t.strip()]
        
        if not todo_id_list:
            return "Error: format todo_ids tidak valid."

        with Session(engine) as session:
            user = _get_user(session, user_id)
            agent_session = _get_agent_session(session, session_id, user)
            todos = []
            for todo_id in todo_id_list:
                todo = todo_service.read_todo_by_id(_parse_uuid(todo_id, "todo_id"), session, user)
                todos.append(todo)

            preview_json = {
                "message": f"{len(todos)} ToDo akan dihapus jika user mengonfirmasi.",
                "items": [_serialize_todo(todo) for todo in todos],
            }
            payload_json = {"todo_ids": [str(todo.id) for todo in todos]}
            pending_action = _create_pending_action(
                session=session,
                user=user,
                agent_session=agent_session,
                action_type="bulk_delete_todos",
                payload_json=payload_json,
                preview_json=preview_json,
            )
            return {
                "requires_confirmation": True,
                "pending_action_id": str(pending_action.id),
                "action_type": "bulk_delete_todos",
                "payload_json": payload_json,
                "preview_json": preview_json,
            }
    except Exception as exc:
        return f"Error: {exc}"


llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=settings.GROQ_API_KEY)
tools = [
    list_todos,
    search_todos,
    create_todo,
    update_todo,
    request_delete_todo_confirmation,
    request_bulk_delete_todos_confirmation,
]

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Anda adalah asisten AI pengelola jadwal yang cerdas. "
                "Selalu gunakan user_id aktif saat memanggil tool. "
                "Gunakan list_todos atau search_todos untuk mencari konteks sebelum update/delete. "
                "create_todo boleh langsung dieksekusi jika instruksi jelas. "
                "update_todo hanya untuk satu ToDo yang todo_id-nya jelas. "
                "Untuk semua permintaan hapus/delete, jangan menghapus langsung; "
                "gunakan request_delete_todo_confirmation atau request_bulk_delete_todos_confirmation. "
                "Saat membuat confirmation request, selalu kirim session_id aktif ke tool. "
                "Jika tool mengembalikan requires_confirmation=true, jelaskan preview aksi dan minta user mengonfirmasi."
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=settings.DEBUG,
    return_intermediate_steps=True,
)


def jalankan_agent(
    chat: str,
    user_id: str | None = None,
    session_id: str | None = None,
    recent_message: list | None = None,
    recent_tool_calls: list | None = None,
):
    """Fungsi jembatan untuk dipanggil oleh server backend."""
    recent_message = recent_message or []
    recent_tool_calls = recent_tool_calls or []

    if not user_id:
        with Session(engine) as session:
            first_user = session.exec(select(User)).first()
            user_id = str(first_user.id) if first_user else "00000000-0000-0000-0000-000000000000"

    sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    konteks_pesan = f"""
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

    respon = agent_executor.invoke({"input": konteks_pesan})

    tool_calls_metadata = []
    for action, observation in respon.get("intermediate_steps", []):
        tool_calls_metadata.append(
            {
                "tool_name": action.tool,
                "input_json": action.tool_input,
                "output_json": observation,
            }
        )

    return {
        "reply": respon["output"],
        "tool_calls": tool_calls_metadata,
    }
