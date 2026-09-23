from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import AuthContext, require_agency_staff
from ..models import TimeEntry
from .tasks import _get_visible_task_or_404

router = APIRouter(prefix="/projects/{project_id}/tasks/{task_id}/time-entries", tags=["time"])


@router.get("", response_model=list[schemas.TimeEntryOut])
def list_time_entries(project_id: str, task_id: str, ctx: AuthContext = Depends(require_agency_staff), db: Session = Depends(get_db)):
    # Clients never see time entries at all -- require_agency_staff blocks
    # client_user before the handler even runs.
    _get_visible_task_or_404(project_id, task_id, ctx, db)
    return db.query(TimeEntry).filter(TimeEntry.task_id == task_id, TimeEntry.agency_id == ctx.agency_id).all()


@router.post("", response_model=schemas.TimeEntryOut)
def log_time(project_id: str, task_id: str, body: schemas.TimeEntryCreate, ctx: AuthContext = Depends(require_agency_staff), db: Session = Depends(get_db)):
    _get_visible_task_or_404(project_id, task_id, ctx, db)
    entry = TimeEntry(
        agency_id=ctx.agency_id, task_id=task_id, user_id=ctx.user_id,
        **body.model_dump(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
