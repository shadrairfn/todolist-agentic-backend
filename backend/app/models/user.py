from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship, text

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: UUID
    
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
    todo: List["Todo"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})