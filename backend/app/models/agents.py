from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

class AgentSessionBase(SQLModel):
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AgentSessionCreate(AgentSessionBase):
    pass

class AgentSessionUpdate(AgentSessionBase):
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AgentSession(AgentSessionBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)

class AgentMessageBase(SQLModel):
    session_id: UUID = Field(foreign_key="agentsession.id", index=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    role: str
    content: str
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
class AgentMessage(AgentMessageBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

class AgentToolCallBase(SQLModel):
    session_id: UUID = Field(foreign_key="agentsession.id", index=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    tool_name: str
    action: str
    input_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    output_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: str
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AgentToolCall(AgentToolCallBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

class PendingActionBase(SQLModel):
    user_id: UUID = Field(foreign_key="user.id", index=True)
    session_id: UUID = Field(foreign_key="agentsession.id", index=True)
    action_type: str = Field(index=True)
    payload_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    preview_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = Field(default="pending", index=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

class PendingAction(PendingActionBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
