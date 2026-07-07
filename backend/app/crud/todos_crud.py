from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from app.models.todo import ChecklistItem, Label, Project, Todo


def list_todos(session: Session, user_id: UUID) -> list[Todo]:
    return session.exec(select(Todo).where(Todo.user_id == user_id)).all()


def get_todo(session: Session, todo_id: UUID) -> Optional[Todo]:
    return session.get(Todo, todo_id)


def save_todo(session: Session, todo: Todo) -> Todo:
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo


def delete_todo(session: Session, todo: Todo) -> None:
    session.delete(todo)
    session.commit()


def list_projects(session: Session, user_id: UUID) -> list[Project]:
    return session.exec(select(Project).where(Project.user_id == user_id)).all()


def get_project(session: Session, project_id: UUID) -> Optional[Project]:
    return session.get(Project, project_id)


def list_labels(session: Session, user_id: UUID) -> list[Label]:
    return session.exec(select(Label).where(Label.user_id == user_id)).all()


def get_label(session: Session, label_id: UUID) -> Optional[Label]:
    return session.get(Label, label_id)


def get_checklist_item(session: Session, item_id: UUID) -> Optional[ChecklistItem]:
    return session.get(ChecklistItem, item_id)


def list_checklist_items(session: Session, todo_id: UUID) -> list[ChecklistItem]:
    statement = select(ChecklistItem).where(ChecklistItem.todo_id == todo_id).order_by(ChecklistItem.position)
    return session.exec(statement).all()
