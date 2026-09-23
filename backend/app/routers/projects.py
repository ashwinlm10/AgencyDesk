from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import AuthContext, get_current_context, require_agency_staff, require_admin
from ..models import Project, ProjectMembership, Client, Task, Comment, Role

router = APIRouter(prefix="/projects", tags=["projects"])


def _visible_project_ids(ctx: AuthContext, db: Session):
    """Central place that decides which project ids a caller may see.
    Every other endpoint that needs 'is this project visible to me' reuses
    this instead of re-deriving the rule, so the rule can't drift between
    the list view and, say, search or comments."""
    q = db.query(Project.id).filter(Project.agency_id == ctx.agency_id)
    if ctx.role == Role.agency_admin:
        return {row.id for row in q.all()}
    if ctx.role == Role.agency_member:
        assigned = db.query(ProjectMembership.project_id).filter(
            ProjectMembership.agency_id == ctx.agency_id,
            ProjectMembership.user_id == ctx.user_id,
        )
        return {row.project_id for row in assigned.all()}
    # client_user: only projects belonging to their own client company
    client_projects = q.filter(Project.client_id == ctx.client_id)
    return {row.id for row in client_projects.all()}


@router.get("", response_model=list[schemas.ProjectOut])
def list_projects(ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)):
    ids = _visible_project_ids(ctx, db)
    if not ids:
        return []
    return db.query(Project).filter(Project.id.in_(ids), Project.agency_id == ctx.agency_id).all()


@router.post("", response_model=schemas.ProjectOut)
def create_project(body: schemas.ProjectCreate, ctx: AuthContext = Depends(require_agency_staff), db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == body.client_id, Client.agency_id == ctx.agency_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found in this agency")
    project = Project(agency_id=ctx.agency_id, client_id=client.id, name=body.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _get_visible_project_or_404(project_id: str, ctx: AuthContext, db: Session) -> Project:
    ids = _visible_project_ids(ctx, db)
    project = db.query(Project).filter(Project.id == project_id, Project.agency_id == ctx.agency_id).first()
    # Returning 404 (not 403) for both "doesn't exist" and "exists but not
    # yours" is deliberate: it stops an attacker from using the status code
    # to enumerate which IDs are valid in another tenant.
    if not project or project.id not in ids:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/members/{user_id}")
def add_project_member(project_id: str, user_id: str, ctx: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
    project = _get_visible_project_or_404(project_id, ctx, db)
    exists = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == project.id, ProjectMembership.user_id == user_id
    ).first()
    if exists:
        return {"status": "already a member"}
    pm = ProjectMembership(agency_id=ctx.agency_id, project_id=project.id, user_id=user_id)
    db.add(pm)
    db.commit()
    return {"status": "added"}


@router.delete("/{project_id}/members/{user_id}")
def remove_project_member(project_id: str, user_id: str, ctx: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
    """Edge case: removing a team member mid-task.

    Decision made here: any task in THIS project still assigned to them
    gets unassigned (not deleted, not left dangling on someone who can no
    longer act on it) and a system comment is left on each affected task so
    there's an audit trail of why it suddenly lost its assignee.
    """
    project = _get_visible_project_or_404(project_id, ctx, db)
    pm = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == project.id, ProjectMembership.user_id == user_id
    ).first()
    if not pm:
        raise HTTPException(status_code=404, detail="Not a member of this project")

    affected_tasks = db.query(Task).filter(
        Task.project_id == project.id, Task.agency_id == ctx.agency_id, Task.assignee_user_id == user_id
    ).all()
    for task in affected_tasks:
        task.assignee_user_id = None
        db.add(Comment(
            agency_id=ctx.agency_id, task_id=task.id, author_user_id=ctx.user_id,
            body="System: previous assignee was removed from this project; task is now unassigned.",
            visibility="internal",
        ))

    db.delete(pm)
    db.commit()
    return {"status": "removed", "unassigned_tasks": len(affected_tasks)}
