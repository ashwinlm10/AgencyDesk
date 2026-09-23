import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import hash_password, verify_password, create_access_token, decode_access_token
from ..database import get_db
from ..models import User, Membership, Agency, Invite, InviteStatus

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup-agency", response_model=schemas.TokenResponse)
def signup_agency(body: schemas.SignupAgency, db: Session = Depends(get_db)):
    """Creates a brand new agency (tenant) plus its first admin user."""
    existing = db.query(User).filter(User.email == body.email).first()
    agency = Agency(name=body.agency_name, slug=f"{body.agency_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}")
    db.add(agency)
    db.flush()

    user = existing
    if not user:
        user = User(email=body.email, hashed_password=hash_password(body.password), name=body.admin_name)
        db.add(user)
        db.flush()

    membership = Membership(user_id=user.id, agency_id=agency.id, role="agency_admin")
    db.add(membership)
    db.commit()

    token = create_access_token({
        "sub": user.id, "scope": "access", "membership_id": membership.id,
    })
    return schemas.TokenResponse(
        access_token=token, role=membership.role, agency_id=agency.id, agency_name=agency.name,
    )


@router.post("/login", response_model=schemas.LoginResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    memberships = db.query(Membership).filter(Membership.user_id == user.id).all()
    if not memberships:
        raise HTTPException(status_code=403, detail="No agency membership found for this account")

    identity_token = create_access_token({"sub": user.id, "scope": "identity"})
    options = []
    for m in memberships:
        agency = db.query(Agency).filter(Agency.id == m.agency_id).first()
        options.append(schemas.MembershipOption(
            membership_id=m.id, agency_id=m.agency_id, agency_name=agency.name, role=m.role,
        ))
    return schemas.LoginResponse(identity_token=identity_token, memberships=options)


@router.post("/select-agency", response_model=schemas.TokenResponse)
def select_agency(body: schemas.SelectAgencyRequest, db: Session = Depends(get_db)):
    """Second step of login: user picks WHICH agency context to operate in.
    This is what keeps the same email cleanly separated across agencies --
    the resulting token is scoped to exactly one membership/role."""
    payload = decode_access_token(body.identity_token)
    if not payload or payload.get("scope") != "identity":
        raise HTTPException(status_code=401, detail="Invalid or expired identity token")

    membership = db.query(Membership).filter(
        Membership.id == body.membership_id, Membership.user_id == payload["sub"]
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="That membership doesn't belong to this account")

    agency = db.query(Agency).filter(Agency.id == membership.agency_id).first()
    token = create_access_token({
        "sub": membership.user_id, "scope": "access", "membership_id": membership.id,
    })
    return schemas.TokenResponse(
        access_token=token, role=membership.role, agency_id=agency.id, agency_name=agency.name,
    )


@router.post("/accept-invite", response_model=schemas.TokenResponse)
def accept_invite(body: schemas.InviteAcceptRequest, db: Session = Depends(get_db)):
    """Idempotent: accepting the same invite twice never creates two
    accounts or two memberships. Once status flips from pending, a second
    call with the same token is rejected outright -- but if the caller
    already has an account+membership from a first successful accept, we
    just hand back a fresh token instead of erroring, since from the
    client's perspective a double-click shouldn't be a scary failure."""
    invite = db.query(Invite).filter(Invite.token == body.token).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.status == InviteStatus.revoked:
        raise HTTPException(status_code=410, detail="Invite has been revoked")

    user = db.query(User).filter(User.email == invite.email).first()

    if invite.status == InviteStatus.accepted:
        # Already accepted earlier -- if it's the SAME account, just log them
        # in again instead of erroring on the double-click / double-submit.
        existing_membership = None
        if user:
            existing_membership = db.query(Membership).filter(
                Membership.user_id == user.id, Membership.agency_id == invite.agency_id
            ).first()
        if not existing_membership:
            raise HTTPException(status_code=409, detail="Invite already used")
        token = create_access_token({
            "sub": user.id, "scope": "access", "membership_id": existing_membership.id,
        })
        agency = db.query(Agency).filter(Agency.id == invite.agency_id).first()
        return schemas.TokenResponse(
            access_token=token, role=existing_membership.role,
            agency_id=agency.id, agency_name=agency.name,
        )

    if not user:
        user = User(email=invite.email, hashed_password=hash_password(body.password), name=body.name)
        db.add(user)
        db.flush()

    membership = db.query(Membership).filter(
        Membership.user_id == user.id, Membership.agency_id == invite.agency_id
    ).first()
    if not membership:
        membership = Membership(
            user_id=user.id, agency_id=invite.agency_id, role=invite.role, client_id=invite.client_id,
        )
        db.add(membership)

    invite.status = InviteStatus.accepted
    from datetime import datetime
    invite.accepted_at = datetime.utcnow()
    db.commit()
    db.refresh(membership)

    agency = db.query(Agency).filter(Agency.id == invite.agency_id).first()
    token = create_access_token({
        "sub": user.id, "scope": "access", "membership_id": membership.id,
    })
    return schemas.TokenResponse(
        access_token=token, role=membership.role, agency_id=agency.id, agency_name=agency.name,
    )
