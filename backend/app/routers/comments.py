from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import AuthContext, get_current_context
from ..models import Comment, Visibility, Role
from .tasks import _get_visible_task_or_404

router = APIRouter(prefix="/projects/{project_id}/tasks/{task_id}/comments", tags=["comments"])


@router.get("", response_model=list[schemas.CommentOut])
def list_comments(project_id: str, task_id: str, ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)):
    _get_visible_task_or_404(project_id, task_id, ctx, db)  # 404s if task isn't visible to caller at all
    q = db.query(Comment).filter(Comment.task_id == task_id, Comment.agency_id == ctx.agency_id)
    if ctx.role == Role.client_user:
        # Same choke-point pattern as tasks: clients never see internal comments,
        # even on a task they ARE allowed to view.
        q = q.filter(Comment.visibility == Visibility.client_visible)
    return q.order_by(Comment.created_at).all()


@router.post("", response_model=schemas.CommentOut)
def create_comment(project_id: str, task_id: str, body: schemas.CommentCreate, ctx: AuthContext = Depends(get_current_context), db: Session = Depends(get_db)):
    _get_visible_task_or_404(project_id, task_id, ctx, db)
    visibility = body.visibility
    if ctx.role == Role.client_user:
        # Clients cannot post an "internal" comment even if they try to --
        # forced server-side regardless of what the request body says.
        visibility = Visibility.client_visible
    comment = Comment(
        agency_id=ctx.agency_id, task_id=task_id, author_user_id=ctx.user_id,
        body=body.body, visibility=visibility,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
