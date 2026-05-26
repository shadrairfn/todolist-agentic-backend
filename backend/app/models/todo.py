# File: backend/app/models/todo.py
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship, text

# 1. Skema Dasar (Field yang diinput oleh client)
class TodoBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    completed: bool = Field(default=False)
    is_daily: bool = Field(default=False)
    is_weekly: bool = Field(default=False)
    is_monthly: bool = Field(default=False)
    is_yearly: bool = Field(default=False)

class TodoCreate(TodoBase):
    pass 

class TodoUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    completed: Optional[bool] = None

class Todo(TodoBase, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4, 
        primary_key=True,
        index=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")}
    )
    
    # Kunci tamu didefinisikan secara khusus di model tabel database
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    
    # Relationship
    user: Optional["User"] = Relationship(back_populates="todos")