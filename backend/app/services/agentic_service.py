from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.security import get_current_user
from app.models.user import User
from app.models.agents import AgentSessionCreate, AgentSession, AgentMessage, AgentToolCall, PendingAction
from app.models.todo import Todo
from sqlmodel import Session, select
from app.db.session import get_session
from datetime import datetime, timedelta
from uuid import UUID
import app.services.todo_service as todo_service

def create_sessions(
    data: AgentSessionCreate, 
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    new_session = AgentSession(
        title=data.title,
        user_id=current_user.id,
        created_at=datetime.now(),
    )

    session.add(new_session)
    session.commit()
    session.refresh(new_session)
    return new_session

def get_all_sessions(
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    sessions = session.query(AgentSession).filter(AgentSession.user_id == current_user.id).all()
    return sessions

def get_session_by_id(
    session_id: UUID, 
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    db_session = session.get(AgentSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        if db_session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke Session ini")
    return db_session

def delete_session_by_id(
    session_id: UUID, 
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    db_session = session.get(AgentSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    if current_user and (isinstance(current_user, User) or type(current_user).__name__ == "User" or hasattr(current_user, "id")):
        if db_session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke Session ini")
    session.delete(db_session)
    session.commit()
    return {"message": f"Session '{db_session.title}' berhasil dihapus"}

def get_all_chat_user(
    session_id: UUID, 
    session: Session= Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    messages = session.query(
        AgentMessage
    ).filter(
        AgentMessage.session_id == session_id, 
        AgentMessage.user_id == current_user.id
    ).all()
    return messages
 
def recent_message(
    session_id: UUID, 
    session: Session= Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    user_messages = session.query(
        AgentMessage.content
    ).filter(
        AgentMessage.session_id == session_id, 
        AgentMessage.user_id == current_user.id, 
        AgentMessage.role == "user"
    ).order_by(AgentMessage.created_at.desc())\
    .limit(5).all()

    agent_messages = session.query(
        AgentMessage.content
    ).filter(
        AgentMessage.session_id == session_id, 
        AgentMessage.user_id == current_user.id, 
        AgentMessage.role == "agent"
    ).order_by(AgentMessage.created_at.desc())\
    .limit(5).all()
    
    response = []

    for i in range(len(user_messages)):
        response.append({
            "user": f"{user_messages[i]}",
            "agent": f"{agent_messages[i]}"
        })
    
    return response
    
def recent_tool_calls(
    session_id:UUID, 
    session: Session= Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    tool_calls = session.query(
        AgentMessage.metadata_json,
        AgentMessage.created_at
    ).filter(
        AgentMessage.session_id == session_id,
        AgentMessage.user_id == current_user.id,
        AgentMessage.role == "agent"
    ).order_by(AgentMessage.created_at.desc())\
    .limit(5).all()
    
    response = []
    for tc in tool_calls:
        metadata = tc.metadata_json or []
        # Jika metadata berupa dict tunggal (bukan list), jadikan list agar bisa di-loop
        if isinstance(metadata, dict):
            metadata = [metadata]
            
        for data in metadata:
            if not isinstance(data, dict):
                continue
                
            raw_output_json = data.get("output_json") or {}
            input_json = data.get("input_json") or {}
            
            # Pastikan input_json dict (biasanya parameter action dari agent adalah dict tunggal)
            if isinstance(input_json, list):
                input_json = input_json[0] if len(input_json) > 0 else {}
            elif not isinstance(input_json, dict):
                input_json = {}
                
            # Jika output_json berupa list, kita loop agar semuanya masuk.
            # Jika berupa dict tunggal, jadikan list berisi 1 elemen agar tetap bisa di-loop.
            output_list = raw_output_json if isinstance(raw_output_json, list) else [raw_output_json]
            
            for out_item in output_list:
                if not isinstance(out_item, dict):
                    out_item = {}
                    
                response.append({
                    "todo_id": out_item.get("id"),
                    "tool_name": data.get("tool_name"),
                    "action": input_json.get("action_method"),
                    "title": out_item.get("title"),
                    "deadline": out_item.get("deadline"),
                    "completed": out_item.get("completed"),
                    "created_at": tc.created_at
                })
    
    return response

def create_pending_action(
    action_type: str,
    payload_json: dict,
    preview_json: dict,
    session_id: UUID,
    session: Session,
    current_user: User,
    expires_in_minutes: int = 10,
):
    get_session_by_id(session_id, session, current_user)
    pending_action = PendingAction(
        user_id=current_user.id,
        session_id=session_id,
        action_type=action_type,
        payload_json=payload_json,
        preview_json=preview_json,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes),
    )
    session.add(pending_action)
    session.commit()
    session.refresh(pending_action)
    return pending_action

def get_pending_actions(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    statement = select(PendingAction).where(
        PendingAction.user_id == current_user.id,
        PendingAction.status == "pending",
    ).order_by(PendingAction.created_at.desc())
    return session.exec(statement).all()

def get_pending_action_by_id(
    pending_action_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pending_action = session.get(PendingAction, pending_action_id)
    if not pending_action:
        raise HTTPException(status_code=404, detail="Pending action tidak ditemukan")
    if pending_action.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke pending action ini")
    return pending_action

def cancel_pending_action(
    pending_action_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pending_action = get_pending_action_by_id(pending_action_id, session, current_user)
    if pending_action.status != "pending":
        raise HTTPException(status_code=400, detail="Pending action sudah tidak aktif")

    pending_action.status = "cancelled"
    pending_action.cancelled_at = datetime.utcnow()
    session.add(pending_action)
    session.commit()
    session.refresh(pending_action)
    return {"message": "Aksi dibatalkan", "pending_action": pending_action}

def _execute_delete_todo(payload: dict, session: Session, current_user: User):
    todo_id = UUID(payload["todo_id"])
    return todo_service.delete_todo(todo_id, session, current_user)

def _execute_bulk_delete_todos(payload: dict, session: Session, current_user: User):
    todo_ids = payload.get("todo_ids") or []
    deleted = []
    for raw_todo_id in todo_ids:
        todo_id = UUID(raw_todo_id)
        todo = session.get(Todo, todo_id)
        if not todo:
            raise HTTPException(status_code=404, detail=f"ToDo {todo_id} tidak ditemukan")
        if todo.user_id != current_user.id:
            raise HTTPException(status_code=403, detail=f"Anda tidak memiliki akses ke ToDo {todo_id}")
        deleted.append({"id": str(todo.id), "title": todo.title})
        session.delete(todo)
    session.commit()
    return {"message": f"{len(deleted)} ToDo berhasil dihapus", "deleted_count": len(deleted), "deleted": deleted}

ACTION_EXECUTORS = {
    "delete_todo": _execute_delete_todo,
    "bulk_delete_todos": _execute_bulk_delete_todos,
}

def confirm_pending_action(
    pending_action_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pending_action = get_pending_action_by_id(pending_action_id, session, current_user)
    if pending_action.status != "pending":
        raise HTTPException(status_code=400, detail="Pending action sudah tidak aktif")
    if pending_action.expires_at < datetime.utcnow():
        pending_action.status = "expired"
        session.add(pending_action)
        session.commit()
        raise HTTPException(status_code=400, detail="Pending action sudah kedaluwarsa")

    executor = ACTION_EXECUTORS.get(pending_action.action_type)
    if not executor:
        raise HTTPException(status_code=400, detail="Action tidak didukung")

    try:
        result = executor(pending_action.payload_json, session, current_user)
        pending_action.status = "confirmed"
        pending_action.confirmed_at = datetime.utcnow()
        tool_status = "success"
        error_message = None
    except Exception as exc:
        result = {"error": str(exc)}
        pending_action.status = "failed"
        tool_status = "failed"
        error_message = str(exc)

    session.add(pending_action)
    db_tool_call = AgentToolCall(
        session_id=pending_action.session_id,
        user_id=current_user.id,
        tool_name="pending_action_executor",
        action=pending_action.action_type,
        input_json=pending_action.payload_json,
        output_json=result,
        status=tool_status,
        error_message=error_message,
        created_at=datetime.utcnow(),
    )
    session.add(db_tool_call)

    message_content = (
        f"Aksi {pending_action.action_type} berhasil dijalankan."
        if tool_status == "success"
        else f"Aksi {pending_action.action_type} gagal dijalankan."
    )
    agent_message = AgentMessage(
        session_id=pending_action.session_id,
        user_id=current_user.id,
        role="agent",
        content=message_content,
        metadata_json={"pending_action_id": str(pending_action.id), "result": result},
        created_at=datetime.utcnow(),
    )
    session.add(agent_message)
    session.commit()
    session.refresh(pending_action)

    if tool_status == "failed":
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "message": "Aksi berhasil dijalankan",
        "pending_action": pending_action,
        "result": result,
    }
