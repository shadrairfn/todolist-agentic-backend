from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.services import todo_service
from typing import Optional
from app.core.config import settings

@tool
def manage_todo_list(
    action_method: str, 
    user_id: str = "", 
    todo_id: str = "", 
    title: str = "", 
    description: str = "", 
    deadline: str = "", 
    completed: Optional[bool] = None,
    is_daily: Optional[bool] = None,
    is_weekly: Optional[bool] = None,
    is_monthly: Optional[bool] = None,
    is_yearly: Optional[bool] = None
):
    """
    Gunakan fungsi ini untuk mengelola jadwal harian atau todo list user (membuat, mengambil/mencari, mengedit, atau menghapus).
    Argumen 'user_id' (ID user aktif) SELALU WAJIB diisi untuk semua tipe action (POST, GET, PATCH, DELETE).

    - Jika 'action_method' berisi 'POST', fungsi akan membuat/menyimpan ToDo baru.
      Argumen 'title' (judul tugas) WAJIB diisi.
      Argumen lainnya ('description', 'deadline', 'completed', 'is_daily', 'is_weekly', 'is_monthly', 'is_yearly') opsional.
    - Jika 'action_method' berisi 'GET', fungsi akan mengambil seluruh ToDo list milik user.
    - Jika 'action_method' berisi 'PATCH', fungsi akan mengedit/mengupdate ToDo yang sudah ada.
      Argumen 'todo_id' (UUID ToDo yang akan diedit) WAJIB diisi.
    - Jika 'action_method' berisi 'DELETE', fungsi akan menghapus ToDo yang sudah ada.
      Argumen 'todo_id' (UUID ToDo yang akan dihapus) WAJIB diisi.
    """
    if not user_id:
        return "Error: Argumen 'user_id' wajib diisi untuk semua tipe action."

    from app.db.session import engine
    from sqlmodel import Session, select
    from app.models.todo import Todo
    from app.models.user import User
    from uuid import UUID

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return f"Error: Format user_id tidak valid ({user_id})"

    import datetime

    deadline_dt = None
    if deadline and str(deadline).strip() != "" and str(deadline).lower() not in ("none", "null", "current_date"):
        deadline_str = str(deadline).strip()
        parsed_dt = None
        
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d",
        ):
            try:
                parsed_dt = datetime.datetime.strptime(deadline_str, fmt)
                break
            except ValueError:
                continue
                
        if not parsed_dt:
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    time_parsed = datetime.datetime.strptime(deadline_str, fmt).time()
                    parsed_dt = datetime.datetime.combine(datetime.date.today(), time_parsed)
                    break
                except ValueError:
                    continue
        
        if not parsed_dt:
            try:
                from dateutil import parser
                parsed_dt = parser.parse(deadline_str)
            except Exception:
                pass
                
        deadline_dt = parsed_dt


    if not description or str(description).strip() == "" or str(description).lower() in ("none", "null"):
        description_clean = None
    else:
        description_clean = description

    with Session(engine) as session:
        if action_method == "POST":
            db_todo = Todo(
                title=title,
                description=description_clean,
                deadline=deadline_dt,
                completed=completed if completed is not None else False,
                is_daily=is_daily if is_daily is not None else False,
                is_weekly=is_weekly if is_weekly is not None else False,
                is_monthly=is_monthly if is_monthly is not None else False,
                is_yearly=is_yearly if is_yearly is not None else False,
                user_id=user_uuid
            )
            return todo_service.create_todo(db_todo, session)
        elif action_method == "GET":
            from app.models.user import User
            user = session.get(User, user_uuid)
            todos = todo_service.read_todos(session, current_user=user)
            return [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "description": t.description,
                    "deadline": str(t.deadline) if t.deadline else None,
                    "completed": t.completed,
                    "is_daily": t.is_daily,
                    "is_weekly": t.is_weekly,
                    "is_monthly": t.is_monthly,
                    "is_yearly": t.is_yearly
                } for t in todos
            ]
        elif action_method == "PATCH":
            if not todo_id:
                return "Error: Argumen 'todo_id' wajib diisi untuk melakukan update/edit."
            
            todo_uuid = UUID(todo_id)
            user_obj = session.get(User, user_uuid)
            db_todo = session.get(Todo, todo_uuid)
            if not db_todo:
                return f"Error: ToDo dengan ID {todo_id} tidak ditemukan."
            
            if db_todo.user_id != user_uuid:
                return "Error: Anda tidak memiliki akses untuk mengedit ToDo ini."
            
            if title and title.strip() != "":
                db_todo.title = title
            if description is not None and description_clean is not None:
                db_todo.description = description_clean
            elif description == "" or description == "None":
                db_todo.description = None
                
            if deadline is not None and deadline_dt is not None:
                db_todo.deadline = deadline_dt
            elif deadline == "" or deadline == "None":
                db_todo.deadline = None
                
            if completed is not None:
                db_todo.completed = completed

            return todo_service.update_todo(todo_uuid, db_todo, session, user_obj)
        elif action_method == "DELETE":
            if not todo_id:
                return "Error: Argumen 'todo_id' wajib diisi untuk melakukan penghapusan."
            
            todo_uuid = UUID(todo_id)
            db_todo = session.get(Todo, todo_uuid)
            if not db_todo:
                return f"Error: ToDo dengan ID {todo_id} tidak ditemukan."
            
            if db_todo.user_id != user_uuid:
                return "Error: Anda tidak memiliki akses untuk menghapus ToDo ini."
            
            session.delete(db_todo)
            session.commit()
            return {"message": f"ToDo dengan judul '{db_todo.title}' berhasil dihapus!"}

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=settings.GROQ_API_KEY)
tools = [manage_todo_list]

prompt = ChatPromptTemplate.from_messages([
    ("system", "Anda adalah asisten AI pengelola jadwal yang cerdas. Gunakan tool yang tersedia untuk menyimpan, mengambil, mengedit (PATCH), atau menghapus (DELETE) jadwal harian/ToDo user. Saat user meminta untuk mengedit atau menghapus tugas yang ada, Anda WAJIB memanggil tool dengan 'action_method' GET terlebih dahulu untuk mencari tugas tersebut dan mendapatkan UUID ('id') tugasnya, kemudian panggil tool kembali dengan 'action_method' PATCH atau DELETE dan sertakan UUID tersebut di parameter 'todo_id'. Pastikan untuk selalu meneruskan 'user_id' (ID User Aktif) ke dalam parameter 'user_id' saat memanggil tool!"),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_tool_calling_agent(
    llm=llm, 
    tools=tools, 
    prompt=prompt
)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True,
    return_intermediate_steps=True
)

def jalankan_agent(chat: str, user_id: str = None, recent_message: list = [], recent_tool_calls: list = []):
    """Fungsi jembatan untuk dipanggil oleh server backend"""
    if not user_id:
        from app.db.session import engine
        from sqlmodel import Session, select
        from app.models.user import User
        with Session(engine) as session:
            first_user = session.exec(select(User)).first()
            if first_user:
                user_id = str(first_user.id)
            else:
                user_id = "00000000-0000-0000-0000-000000000000" 

    import datetime
    sekarang = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    konteks_pesan = f"""
    Waktu Sekarang (Today's Datetime): {sekarang}

    System:
    Kamu adalah agent todo list yang digunakan untuk mengelola jadwal harian/ToDo user.
    Gunakan tool yang tersedia untuk menyimpan, mengambil, mengedit (PATCH), atau menghapus (DELETE) jadwal harian/ToDo user. 
    Saat user meminta untuk mengedit atau menghapus tugas yang ada, 
    Anda WAJIB memanggil tool dengan 'action_method' GET terlebih dahulu untuk mencari tugas tersebut dan mendapatkan UUID ('id') tugasnya, 
    kemudian panggil tool kembali dengan 'action_method' PATCH atau DELETE dan sertakan UUID tersebut di parameter 'todo_id'. 
    Pastikan untuk selalu meneruskan 'user_id' (ID User Aktif) ke dalam parameter 'user_id' saat memanggil tool!

    Current user:
    user_id = {user_id}

    Recent messages:
    {recent_message}

    Recent tool calls:
    {recent_tool_calls}

    Current user message:
    {chat}
    """
    
    respon = agent_executor.invoke({"input": konteks_pesan})
    
    tool_calls_metadata = []
    if "intermediate_steps" in respon:
        for action, observation in respon["intermediate_steps"]:
            # action adalah objek AgentAction, observation adalah output dari tool
            tool_calls_metadata.append({
                "tool_name": action.tool,
                "input_json": action.tool_input,
                "output_json": observation
            })
            
    return {
        "reply": respon["output"],
        "tool_calls": tool_calls_metadata
    }