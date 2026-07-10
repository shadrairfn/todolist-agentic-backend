from datetime import datetime, time, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_
from sqlmodel import Session, select

from app.crud import todos_crud
from app.models.todo import (
    ChecklistItem,
    Label,
    Project,
    Todo,
    TodoCreate,
    TodoLabelLink,
    TodoPriority,
    TodoStatus,
    TodoUpdate,
)
from app.models.user import User
from app.schemas.todo import (
    ChecklistItemCreate,
    ChecklistItemUpdate,
    LabelCreate,
    LabelUpdate,
    ProjectCreate,
    ProjectUpdate,
)


def read_todos(session: Session, current_user: User):
    return _with_progress(todos_crud.list_todos(session, current_user.id))


def read_todo_by_id(todo_id: UUID, session: Session, current_user: User):
    return _with_progress_one(_get_owned_todo(todo_id, session, current_user))


def search_todos(q: str, session: Session, current_user: User):
    return filter_todos(session=session, current_user=current_user, q=q)


def filter_todos(
    session: Session,
    current_user: User,
    q: Optional[str] = None,
    project_id: Optional[UUID] = None,
    label_id: Optional[UUID] = None,
    status: Optional[TodoStatus] = None,
    priority: Optional[TodoPriority] = None,
    overdue: bool = False,
    due_today: bool = False,
    due_this_week: bool = False
):
    statement = _base_todo_statement(current_user)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(or_(Todo.title.ilike(pattern), Todo.description.ilike(pattern)))
    if project_id:
        _get_owned_project(project_id, session, current_user)
        statement = statement.where(Todo.project_id == project_id)
    if label_id:
        _get_owned_label(label_id, session, current_user)
        statement = statement.join(TodoLabelLink).where(TodoLabelLink.label_id == label_id)
    if status:
        statement = statement.where(Todo.status == _enum_value(status))
    if priority:
        statement = statement.where(Todo.priority == _enum_value(priority))
    if overdue:
        statement = statement.where(Todo.due_at < datetime.now(), Todo.status != TodoStatus.done.value)
    if due_today:
        start, end = _today_bounds()
        statement = statement.where(Todo.due_at >= start, Todo.due_at < end)
    if due_this_week:
        start, end = _week_bounds()
        statement = statement.where(Todo.due_at >= start, Todo.due_at < end)
    statement = statement.order_by(Todo.start_at)
    return _with_progress(session.exec(statement).all())


def create_todo(todo: TodoCreate | Todo, session: Session, current_user: User):
    db_todo = todo if isinstance(todo, Todo) else Todo(**todo.model_dump())
    db_todo.user_id = current_user.id
    _validate_project(db_todo.project_id, session, current_user)
    _sync_status_and_completed(db_todo)
    _normalize_enum_fields(db_todo)

    return _with_progress_one(todos_crud.save_todo(session, db_todo))


def update_todo(todo_id: UUID, todo: TodoUpdate, session: Session, current_user: User):
    db_todo = _get_owned_todo(todo_id, session, current_user)
    update_data = todo.model_dump(exclude_unset=True)
    if "deadline" in update_data:
        deadline = update_data.pop("deadline")
        update_data.setdefault("due_at", deadline)

    if "project_id" in update_data:
        _validate_project(update_data["project_id"], session, current_user)

    for key, value in update_data.items():
        setattr(db_todo, key, value)

    _sync_status_and_completed(db_todo, update_data)
    _normalize_enum_fields(db_todo)
    return _with_progress_one(todos_crud.save_todo(session, db_todo))


def delete_todo(todo_id: UUID, session: Session, current_user: User):
    db_todo = _get_owned_todo(todo_id, session, current_user)
    todos_crud.delete_todo(session, db_todo)
    return {"message": f"ToDo '{db_todo.title}' berhasil dihapus"}


def create_project(project: ProjectCreate, session: Session, current_user: User):
    db_project = Project(**project.model_dump(), user_id=current_user.id)
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    return db_project


def list_projects(session: Session, current_user: User):
    return todos_crud.list_projects(session, current_user.id)


def read_project(project_id: UUID, session: Session, current_user: User):
    return _get_owned_project(project_id, session, current_user)


def update_project(project_id: UUID, project: ProjectUpdate, session: Session, current_user: User):
    db_project = _get_owned_project(project_id, session, current_user)
    db_project.sqlmodel_update(project.model_dump(exclude_unset=True))
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    return db_project


def delete_project(project_id: UUID, session: Session, current_user: User):
    db_project = _get_owned_project(project_id, session, current_user)
    for todo in db_project.todos:
        todo.project_id = None
        session.add(todo)
    session.delete(db_project)
    session.commit()
    return {"message": f"Project '{db_project.name}' berhasil dihapus"}


def list_todos_by_project(project_id: UUID, session: Session, current_user: User):
    _get_owned_project(project_id, session, current_user)
    return filter_todos(session=session, current_user=current_user, project_id=project_id)


def create_label(label: LabelCreate, session: Session, current_user: User):
    db_label = Label(**label.model_dump(), user_id=current_user.id)
    session.add(db_label)
    session.commit()
    session.refresh(db_label)
    return db_label


def list_labels(session: Session, current_user: User):
    return todos_crud.list_labels(session, current_user.id)


def read_label(label_id: UUID, session: Session, current_user: User):
    return _get_owned_label(label_id, session, current_user)


def update_label(label_id: UUID, label: LabelUpdate, session: Session, current_user: User):
    db_label = _get_owned_label(label_id, session, current_user)
    db_label.sqlmodel_update(label.model_dump(exclude_unset=True))
    session.add(db_label)
    session.commit()
    session.refresh(db_label)
    return db_label


def delete_label(label_id: UUID, session: Session, current_user: User):
    db_label = _get_owned_label(label_id, session, current_user)
    for todo in list(db_label.todos):
        todo.labels.remove(db_label)
        session.add(todo)
    session.delete(db_label)
    session.commit()
    return {"message": f"Label '{db_label.name}' berhasil dihapus"}


def attach_label(todo_id: UUID, label_id: UUID, session: Session, current_user: User):
    todo = _get_owned_todo(todo_id, session, current_user)
    label = _get_owned_label(label_id, session, current_user)
    if label not in todo.labels:
        todo.labels.append(label)
        session.add(todo)
        session.commit()
        session.refresh(todo)
    return _with_progress_one(todo)


def detach_label(todo_id: UUID, label_id: UUID, session: Session, current_user: User):
    todo = _get_owned_todo(todo_id, session, current_user)
    label = _get_owned_label(label_id, session, current_user)
    if label in todo.labels:
        todo.labels.remove(label)
        session.add(todo)
        session.commit()
        session.refresh(todo)
    return _with_progress_one(todo)


def create_checklist_item(
    todo_id: UUID,
    item: ChecklistItemCreate,
    session: Session,
    current_user: User,
):
    _get_owned_todo(todo_id, session, current_user)
    db_item = ChecklistItem(**item.model_dump(), todo_id=todo_id)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def list_checklist_items(todo_id: UUID, session: Session, current_user: User):
    _get_owned_todo(todo_id, session, current_user)
    return todos_crud.list_checklist_items(session, todo_id)


def update_checklist_item(
    todo_id: UUID,
    item_id: UUID,
    item: ChecklistItemUpdate,
    session: Session,
    current_user: User,
):
    _get_owned_todo(todo_id, session, current_user)
    db_item = _get_checklist_item(item_id, todo_id, session)
    db_item.sqlmodel_update(item.model_dump(exclude_unset=True))
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def delete_checklist_item(todo_id: UUID, item_id: UUID, session: Session, current_user: User):
    _get_owned_todo(todo_id, session, current_user)
    db_item = _get_checklist_item(item_id, todo_id, session)
    session.delete(db_item)
    session.commit()
    return {"message": f"Checklist item '{db_item.title}' berhasil dihapus"}


def checklist_progress(todo_id: UUID, session: Session, current_user: User):
    todo = _get_owned_todo(todo_id, session, current_user)
    return {"todo_id": todo.id, "progress": _calculate_progress(todo)}


def _base_todo_statement(current_user: User):
    return select(Todo).where(Todo.user_id == current_user.id)


def _get_owned_todo(todo_id: UUID, session: Session, current_user: User):
    todo = todos_crud.get_todo(session, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="ToDo tidak ditemukan")
    if todo.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke ToDo ini")
    return todo


def _get_owned_project(project_id: UUID, session: Session, current_user: User):
    project = todos_crud.get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    if project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke Project ini")
    return project


def _get_owned_label(label_id: UUID, session: Session, current_user: User):
    label = todos_crud.get_label(session, label_id)
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    if label.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke Label ini")
    return label


def _get_checklist_item(item_id: UUID, todo_id: UUID, session: Session):
    item = todos_crud.get_checklist_item(session, item_id)
    if not item or item.todo_id != todo_id:
        raise HTTPException(status_code=404, detail="Checklist item tidak ditemukan")
    return item


def _validate_project(project_id: Optional[UUID], session: Session, current_user: User) -> None:
    if project_id:
        _get_owned_project(project_id, session, current_user)





def _sync_status_and_completed(todo: Todo, update_data: Optional[dict] = None) -> None:
    update_data = update_data or {}
    if update_data.get("completed") is True and "status" not in update_data:
        todo.status = TodoStatus.done
    elif update_data.get("completed") is False and "status" not in update_data and _enum_value(todo.status) == TodoStatus.done.value:
        todo.status = TodoStatus.todo

    if _enum_value(update_data.get("status")) == TodoStatus.done.value:
        todo.completed = True
    elif "status" in update_data and _enum_value(update_data["status"]) != TodoStatus.done.value:
        todo.completed = False
    elif not update_data and todo.completed:
        todo.status = TodoStatus.done


def _normalize_enum_fields(todo: Todo) -> None:
    todo.status = _enum_value(todo.status)
    todo.priority = _enum_value(todo.priority)


def _enum_value(value):
    if isinstance(value, Enum):
        return value.value
    return value


def _today_bounds():
    today = datetime.now().date()
    return datetime.combine(today, time.min), datetime.combine(today + timedelta(days=1), time.min)

def _week_bounds():
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=7)
    return datetime.combine(start_of_week, time.min), datetime.combine(end_of_week, time.min)
    
def _calculate_progress(todo: Todo) -> float:
    total = len(todo.checklist_items)
    if total == 0:
        return 1.0 if todo.completed or _enum_value(todo.status) == TodoStatus.done.value else 0.0
    done = len([item for item in todo.checklist_items if item.completed])
    return done / total


def _with_progress(todos: list[Todo]) -> list[Todo]:
    return [_with_progress_one(todo) for todo in todos]


def _with_progress_one(todo: Todo) -> Todo:
    object.__setattr__(todo, "checklist_progress", _calculate_progress(todo))
    return todo
