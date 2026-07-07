"""expand todo workspace foundation

Revision ID: 20260703_0001
Revises:
Create Date: 2026-07-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "20260703_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_id"), "project", ["id"], unique=False)
    op.create_index(op.f("ix_project_name"), "project", ["name"], unique=False)
    op.create_index(op.f("ix_project_user_id"), "project", ["user_id"], unique=False)

    op.create_table(
        "label",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("color", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_label_id"), "label", ["id"], unique=False)
    op.create_index(op.f("ix_label_name"), "label", ["name"], unique=False)
    op.create_index(op.f("ix_label_user_id"), "label", ["user_id"], unique=False)

    op.add_column("todo", sa.Column("due_at", sa.DateTime(), nullable=True))
    op.add_column("todo", sa.Column("reminder_at", sa.DateTime(), nullable=True))
    op.add_column(
        "todo",
        sa.Column("status", sa.String(), server_default="todo", nullable=False),
    )
    op.add_column(
        "todo",
        sa.Column("priority", sa.String(), server_default="medium", nullable=False),
    )
    op.add_column("todo", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_todo_due_at"), "todo", ["due_at"], unique=False)
    op.create_index(op.f("ix_todo_reminder_at"), "todo", ["reminder_at"], unique=False)
    op.create_index(op.f("ix_todo_project_id"), "todo", ["project_id"], unique=False)
    op.create_foreign_key("fk_todo_project_id_project", "todo", "project", ["project_id"], ["id"])

    op.execute("UPDATE todo SET due_at = deadline WHERE due_at IS NULL AND deadline IS NOT NULL")
    op.execute("UPDATE todo SET status = 'done' WHERE completed = true")

    op.create_table(
        "todolabellink",
        sa.Column("todo_id", sa.Uuid(), nullable=False),
        sa.Column("label_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["label_id"], ["label.id"]),
        sa.ForeignKeyConstraint(["todo_id"], ["todo.id"]),
        sa.PrimaryKeyConstraint("todo_id", "label_id"),
    )
    op.create_table(
        "checklistitem",
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("todo_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["todo_id"], ["todo.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_checklistitem_id"), "checklistitem", ["id"], unique=False)
    op.create_index(op.f("ix_checklistitem_title"), "checklistitem", ["title"], unique=False)
    op.create_index(op.f("ix_checklistitem_todo_id"), "checklistitem", ["todo_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_checklistitem_todo_id"), table_name="checklistitem")
    op.drop_index(op.f("ix_checklistitem_title"), table_name="checklistitem")
    op.drop_index(op.f("ix_checklistitem_id"), table_name="checklistitem")
    op.drop_table("checklistitem")
    op.drop_table("todolabellink")
    op.drop_constraint("fk_todo_project_id_project", "todo", type_="foreignkey")
    op.drop_index(op.f("ix_todo_project_id"), table_name="todo")
    op.drop_index(op.f("ix_todo_reminder_at"), table_name="todo")
    op.drop_index(op.f("ix_todo_due_at"), table_name="todo")
    op.drop_column("todo", "project_id")
    op.drop_column("todo", "priority")
    op.drop_column("todo", "status")
    op.drop_column("todo", "reminder_at")
    op.drop_column("todo", "due_at")
    op.drop_index(op.f("ix_label_user_id"), table_name="label")
    op.drop_index(op.f("ix_label_name"), table_name="label")
    op.drop_index(op.f("ix_label_id"), table_name="label")
    op.drop_table("label")
    op.drop_index(op.f("ix_project_user_id"), table_name="project")
    op.drop_index(op.f("ix_project_name"), table_name="project")
    op.drop_index(op.f("ix_project_id"), table_name="project")
    op.drop_table("project")
