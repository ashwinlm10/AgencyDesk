from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import AuthContext, require_agency_staff
from ..models import Client

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[schemas.ClientOut])
def list_clients(ctx: AuthContext = Depends(require_agency_staff), db: Session = Depends(get_db)):
    # Every query filters by agency_id -- this is the tenant-isolation rule,
    # applied identically on every single route in this codebase.
    return db.query(Client).filter(Client.agency_id == ctx.agency_id).all()


@router.post("", response_model=schemas.ClientOut)
def create_client(body: schemas.ClientCreate, ctx: AuthContext = Depends(require_agency_staff), db: Session = Depends(get_db)):
    client = Client(agency_id=ctx.agency_id, name=body.name)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client
