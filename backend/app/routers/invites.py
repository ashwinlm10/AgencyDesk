from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import AuthContext, require_admin
from ..models import Invite, InviteStatus

router = APIRouter(prefix="/invites", tags=["invites"])


@router.post("", response_model=schemas.InviteOut)
def create_or_resend_invite(body: schemas.InviteCreate, ctx: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
    """Edge case: invite races. A partial unique index on
    (agency_id, email) WHERE status='pending' (see migration) makes it
    impossible for two pending invites to exist for the same email in the
    same agency. So 'resend' is just: find the existing pending invite and
    reuse its token, rather than inserting a new row and racing the
    constraint. Clicking "resend" ten times in a row still only ever
    produces one pending invite.
    """
    existing = db.query(Invite).filter(
        Invite.agency_id == ctx.agency_id, Invite.email == body.email, Invite.status == InviteStatus.pending,
    ).first()
    if existing:
        # "resend" -- same token, same row, nothing duplicated. In a real
        # system this is where we'd re-send the email with the same link.
        return existing

    invite = Invite(agency_id=ctx.agency_id, email=body.email, role=body.role, client_id=body.client_id)
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


@router.get("", response_model=list[schemas.InviteOut])
def list_invites(ctx: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(Invite).filter(Invite.agency_id == ctx.agency_id).all()
