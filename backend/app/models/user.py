from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship, text

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    password: str
    name: Optional[str] = None

class UserCreate(UserBase):
    pass 

class UserUpdate(SQLModel):
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None

class User(UserBase, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4, 
        primary_key=True,
        index=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")}
    )
    
    # Relationship
    todos: List["Todo"] = Relationship(back_populates="user")