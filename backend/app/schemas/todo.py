from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import SQLModel

from app.models.todo import TodoPriority, TodoStatus


class ProjectCreate(SQLModel):
    name: str
    description: Optional[str] = None


class ProjectUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectRead(ProjectCreate):
    id: UUID
    user_id: Optional[UUID] = None


class LabelCreate(SQLModel):
    name: str
    color: Optional[str] = None


class LabelUpdate(SQLModel):
    name: Optional[str] = None
    color: Optional[str] = None


class LabelRead(LabelCreate):
    id: UUID
    user_id: Optional[UUID] = None


class ChecklistItemCreate(SQLModel):
    title: str
    completed: bool = False
    position: int = 0


class ChecklistItemUpdate(SQLModel):
    title: Optional[str] = None
    completed: Optional[bool] = None
    position: Optional[int] = None


class ChecklistItemRead(ChecklistItemCreate):
    id: UUID
    todo_id: UUID


class TodoRead(SQLModel):
    id: UUID
    title: str
    description: Optional[str] = None
    start_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    completed: bool
    status: TodoStatus
    priority: TodoPriority
    project_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    is_daily: bool
    is_weekly: bool
    is_monthly: bool
    is_yearly: bool
    checklist_progress: float = 0
