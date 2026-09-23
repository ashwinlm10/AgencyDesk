import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File as FastAPIFile, Form, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import AuthContext, get_current_context, require_agency_staff
from ..models import FileAsset, Visibility, Role, ApprovalStatus
from .tasks import _get_visible_task_or_404

router = APIRouter(prefix="/projects/{project_id}/tasks/{task_id}/files", tags=["files"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/agencydesk_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _file_query(project_id: str, task_id: str, ctx: AuthContext, db: Session):
    q = db.query(FileAsset).filter(FileAsset.task_id == task_id, FileAsset.agency_id == ctx.agency_id)
    if ctx.role == Role.client_user:
        q = q.filter(FileAsset.visibility == Visibility.client_visible)
    return q


@router.get("", response_model=list[schemas.FileOut])
def list_files(project_id: str, task_id: str, ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)):
    _get_visible_task_or_404(project_id, task_id, ctx, db)
    return _file_query(project_id, task_id, ctx, db).all()


@router.post("", response_model=schemas.FileOut)
def upload_file(
    project_id: str, task_id: str,
    visibility: Visibility = Form(Visibility.internal),
    upload: UploadFile = FastAPIFile(...),
    ctx: AuthContext = Depends(require_agency_staff),
    db: Session = Depends(get_db),
):
    _get_visible_task_or_404(project_id, task_id, ctx, db)
    dest_name = f"{uuid.uuid4()}_{upload.filename}"
    dest_path = os.path.join(UPLOAD_DIR, dest_name)
    with open(dest_path, "wb") as f:
        f.write(upload.file.read())

    asset = FileAsset(
        agency_id=ctx.agency_id, task_id=task_id, uploaded_by_user_id=ctx.user_id,
        filename=upload.filename, storage_path=dest_path, visibility=visibility,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.patch("/{file_id}/approval", response_model=schemas.FileOut)
def set_approval(
    project_id: str, task_id: str, file_id: str, body: schemas.FileApprovalUpdate,
    ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db),
):
    if ctx.role != Role.client_user:
        raise HTTPException(status_code=403, detail="Only clients approve files")
    asset = _file_query(project_id, task_id, ctx, db).filter(FileAsset.id == file_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="File not found")
    asset.approval_status = body.approval_status
    db.commit()
    db.refresh(asset)
    return asset
