from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.todo import ProjectCreate, ProjectRead, ProjectUpdate, TodoRead
from app.services import todo_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectRead)
def create_project(
    project: ProjectCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.create_project(project, session, current_user)


@router.get("/", response_model=list[ProjectRead])
def list_projects(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.list_projects(session, current_user)


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(
    project_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.read_project(project_id, session, current_user)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    project: ProjectUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.update_project(project_id, project, session, current_user)


@router.delete("/{project_id}")
def delete_project(
    project_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.delete_project(project_id, session, current_user)


@router.get("/{project_id}/todos", response_model=list[TodoRead])
def list_todos_by_project(
    project_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return todo_service.list_todos_by_project(project_id, session, current_user)
