from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import schemas
from ..database import get_db
from ..deps import AuthContext, get_current_context
from ..models import Task, TimeEntry, Role, Visibility
from .projects import _get_visible_project_or_404

router = APIRouter(prefix="/projects/{project_id}/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.ProjectDashboard)
def project_dashboard(project_id: str, ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)):
    _get_visible_project_or_404(project_id, ctx, db)

    task_q = db.query(Task).filter(Task.project_id == project_id, Task.agency_id == ctx.agency_id)
    time_q = db.query(TimeEntry).filter(TimeEntry.task_id.in_(
        db.query(Task.id).filter(Task.project_id == project_id, Task.agency_id == ctx.agency_id)
    ))

    if ctx.role == Role.client_user:
        # Dashboard is "scoped to what the viewer is allowed to see" --
        # a client's counts only ever reflect client_visible tasks, and
        # clients never see hours logged (internal ops detail) at all.
        task_q = task_q.filter(Task.visibility == Visibility.client_visible)
        total_hours = 0.0
    else:
        total_minutes = time_q.with_entities(func.coalesce(func.sum(TimeEntry.duration_minutes), 0)).scalar()
        total_hours = round(total_minutes / 60, 2)

    counts = {}
    for status, count in task_q.with_entities(Task.status, func.count(Task.id)).group_by(Task.status).all():
        counts[status.value if hasattr(status, "value") else status] = count

    return schemas.ProjectDashboard(project_id=project_id, task_counts_by_status=counts, total_hours=total_hours)
