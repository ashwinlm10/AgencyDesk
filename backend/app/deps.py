from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .auth import decode_access_token
from .database import get_db
from .models import Membership, Role

bearer_scheme = HTTPBearer()


@dataclass
class AuthContext:
    """Everything a route needs to know about 'who is calling, in which
    agency, with which role'. Every query in every router is filtered by
    ctx.agency_id -- there is no code path that queries without it."""
    user_id: str
    agency_id: str
    membership_id: str
    role: Role
    client_id: str | None


def get_current_context(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    payload = decode_access_token(creds.credentials)
    if not payload or payload.get("scope") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    membership_id = payload.get("membership_id")
    # Re-fetch the membership live (not just trust the token) so that a
    # mid-session removal (e.g. admin kicks a member) takes effect immediately
    # instead of the stale token still working until it expires.
    membership = db.query(Membership).filter(Membership.id == membership_id).first()
    if not membership:
        raise HTTPException(status_code=401, detail="Membership no longer exists")

    return AuthContext(
        user_id=membership.user_id,
        agency_id=membership.agency_id,
        membership_id=membership.id,
        role=membership.role,
        client_id=membership.client_id,
    )


def require_roles(*roles: Role):
    def checker(ctx: AuthContext = Depends(get_current_context)) -> AuthContext:
        if ctx.role not in roles:
            raise HTTPException(status_code=403, detail="Not permitted for this role")
        return ctx
    return checker


require_agency_staff = require_roles(Role.agency_admin, Role.agency_member)
require_admin = require_roles(Role.agency_admin)
