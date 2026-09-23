from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import AuthContext, get_current_context, require_agency_staff
from ..models import Task, Visibility, Role
from .projects import _get_visible_project_or_404

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])


def _task_query(project_id: str, ctx: AuthContext, db: Session):
    q = db.query(Task).filter(Task.project_id == project_id, Task.agency_id == ctx.agency_id)
    if ctx.role == Role.client_user:
        # This is the single choke point for "internal never leaks to a
        # client": every task read for a client goes through here, so the
        # filter can't be forgotten on some other list/search/filter screen.
        q = q.filter(Task.visibility == Visibility.client_visible)
    return q


@router.get("", response_model=list[schemas.TaskOut])
def list_tasks(project_id: str, ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)):
    _get_visible_project_or_404(project_id, ctx, db)
    return _task_query(project_id, ctx, db).all()


@router.post("", response_model=schemas.TaskOut)
def create_task(project_id: str, body: schemas.TaskCreate, ctx: AuthContext = Depends(require_agency_staff), db: Session = Depends(get_db)):
    project = _get_visible_project_or_404(project_id, ctx, db)
    task = Task(agency_id=ctx.agency_id, project_id=project.id, **body.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _get_visible_task_or_404(project_id: str, task_id: str, ctx: AuthContext, db: Session) -> Task:
    _get_visible_project_or_404(project_id, ctx, db)
    task = _task_query(project_id, ctx, db).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}", response_model=schemas.TaskOut)
def get_task(project_id: str, task_id: str, ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)):
    return _get_visible_task_or_404(project_id, task_id, ctx, db)


@router.patch("/{task_id}", response_model=schemas.TaskOut)
def update_task(project_id: str, task_id: str, body: schemas.TaskUpdate, ctx: AuthContext = Depends(require_agency_staff), db: Session = Depends(get_db)):
    # require_agency_staff already blocks client_user at the dependency
    # level -- clients can never reach this route to change status/fields.
    task = _get_visible_task_or_404(project_id, task_id, ctx, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task
