from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
from sqlalchemy import Column, String
from sqlmodel import SQLModel, Field, Relationship, text

class TodoPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TodoStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    archived = "archived"


class TodoLabelLink(SQLModel, table=True):
    todo_id: UUID = Field(foreign_key="todo.id", ondelete="CASCADE", primary_key=True)
    label_id: UUID = Field(foreign_key="label.id", ondelete="CASCADE", primary_key=True)


class ProjectBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None


class Project(ProjectBase, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", ondelete="CASCADE", index=True)

    todos: List["Todo"] = Relationship(back_populates="project")


class LabelBase(SQLModel):
    name: str = Field(index=True)
    color: Optional[str] = None


class Label(LabelBase, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", ondelete="CASCADE", index=True)

    todos: List["Todo"] = Relationship(back_populates="labels", link_model=TodoLabelLink)


class ChecklistItemBase(SQLModel):
    title: str = Field(index=True)
    completed: bool = Field(default=False)
    position: int = Field(default=0)


class ChecklistItem(ChecklistItemBase, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    todo_id: UUID = Field(foreign_key="todo.id", ondelete="CASCADE", index=True)

    todo: Optional["Todo"] = Relationship(back_populates="checklist_items")


class TodoBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None
    start_at: Optional[datetime] = None
    due_at: Optional[datetime] = Field(default=None, index=True)
    reminder_at: Optional[datetime] = Field(default=None, index=True)
    completed: bool = Field(default=False)
    status: TodoStatus = Field(
        default=TodoStatus.todo,
        sa_column=Column(String, nullable=False, server_default=TodoStatus.todo.value),
    )
    priority: TodoPriority = Field(
        default=TodoPriority.medium,
        sa_column=Column(String, nullable=False, server_default=TodoPriority.medium.value),
    )
    project_id: Optional[UUID] = Field(default=None, foreign_key="project.id", ondelete="CASCADE", index=True)
    is_daily: bool = Field(default=False)
    is_weekly: bool = Field(default=False)
    is_monthly: bool = Field(default=False)
    is_yearly: bool = Field(default=False)

    @property
    def deadline(self) -> Optional[datetime]:
        return self.due_at

    @deadline.setter
    def deadline(self, value: Optional[datetime]) -> None:
        self.due_at = value

class TodoCreate(TodoBase):
    pass 

class TodoUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    start_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    completed: Optional[bool] = None
    status: Optional[TodoStatus] = None
    priority: Optional[TodoPriority] = None
    project_id: Optional[UUID] = None
    is_daily: Optional[bool] = None
    is_weekly: Optional[bool] = None
    is_monthly: Optional[bool] = None
    is_yearly: Optional[bool] = None

class Todo(TodoBase, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4, 
        primary_key=True,
        index=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")}
    )
    
    # Kunci tamu didefinisikan secara khusus di model tabel database
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", ondelete="CASCADE")
    
    # Relationship
    user: Optional["User"] = Relationship(back_populates="todos")
    project: Optional[Project] = Relationship(back_populates="todos")
    labels: List[Label] = Relationship(back_populates="todos", link_model=TodoLabelLink)
    checklist_items: List[ChecklistItem] = Relationship(
        back_populates="todo",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
