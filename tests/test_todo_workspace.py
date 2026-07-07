from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.models.todo import TodoCreate, TodoPriority, TodoStatus, TodoUpdate
from app.models.user import User
from app.schemas.todo import ChecklistItemCreate, LabelCreate, ProjectCreate
from app.services import todo_service


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture()
def user(session):
    user = User(email="owner@example.com", password="secret", name="Owner")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_create_todo_syncs_due_priority_and_status(session, user):
    due_at = datetime.now() + timedelta(days=2)
    reminder_at = datetime.now() + timedelta(days=1)

    todo = todo_service.create_todo(
        TodoCreate(
            title="Plan launch",
            due_at=due_at,
            reminder_at=reminder_at,
            priority=TodoPriority.urgent,
            status=TodoStatus.in_progress,
        ),
        session,
        user,
    )

    assert todo.deadline == due_at
    assert todo.priority == TodoPriority.urgent
    assert todo.status == TodoStatus.in_progress
    assert todo.completed is False
    assert todo.reminder_at == reminder_at


def test_completed_and_status_stay_compatible(session, user):
    todo = todo_service.create_todo(TodoCreate(title="Ship"), session, user)

    done = todo_service.update_todo(todo.id, TodoUpdate(completed=True), session, user)
    assert done.status == TodoStatus.done
    assert done.completed is True

    reopened = todo_service.update_todo(todo.id, TodoUpdate(status=TodoStatus.todo), session, user)
    assert reopened.status == TodoStatus.todo
    assert reopened.completed is False


def test_project_crud_and_project_filter(session, user):
    project = todo_service.create_project(ProjectCreate(name="Workspace"), session, user)
    todo_service.create_todo(TodoCreate(title="Inside", project_id=project.id), session, user)
    todo_service.create_todo(TodoCreate(title="Outside"), session, user)

    project_todos = todo_service.list_todos_by_project(project.id, session, user)

    assert len(project_todos) == 1
    assert project_todos[0].title == "Inside"


def test_label_attach_detach_and_label_filter(session, user):
    label = todo_service.create_label(LabelCreate(name="Focus", color="#ffcc00"), session, user)
    todo = todo_service.create_todo(TodoCreate(title="Deep work"), session, user)

    todo_service.attach_label(todo.id, label.id, session, user)
    filtered = todo_service.filter_todos(session=session, current_user=user, label_id=label.id)
    assert [item.id for item in filtered] == [todo.id]

    todo_service.detach_label(todo.id, label.id, session, user)
    assert todo_service.filter_todos(session=session, current_user=user, label_id=label.id) == []


def test_checklist_crud_and_progress(session, user):
    todo = todo_service.create_todo(TodoCreate(title="Prepare deck"), session, user)
    first = todo_service.create_checklist_item(
        todo.id,
        ChecklistItemCreate(title="Outline", completed=True, position=1),
        session,
        user,
    )
    todo_service.create_checklist_item(
        todo.id,
        ChecklistItemCreate(title="Review", completed=False, position=2),
        session,
        user,
    )

    progress = todo_service.checklist_progress(todo.id, session, user)
    assert progress["progress"] == 0.5

    todo_service.delete_checklist_item(todo.id, first.id, session, user)
    assert len(todo_service.list_checklist_items(todo.id, session, user)) == 1


def test_search_and_filters(session, user):
    yesterday = datetime.now() - timedelta(days=1)
    today = datetime.now() + timedelta(hours=1)
    todo_service.create_todo(
        TodoCreate(title="Write report", description="Quarterly numbers", due_at=yesterday),
        session,
        user,
    )
    todo_service.create_todo(
        TodoCreate(title="Standup", due_at=today, priority=TodoPriority.high),
        session,
        user,
    )

    assert len(todo_service.search_todos("numbers", session, user)) == 1
    assert len(todo_service.filter_todos(session=session, current_user=user, overdue=True)) == 1
    assert len(todo_service.filter_todos(session=session, current_user=user, due_today=True)) == 1
    assert len(todo_service.filter_todos(session=session, current_user=user, priority=TodoPriority.high)) == 1
