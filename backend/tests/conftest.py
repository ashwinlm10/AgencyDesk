import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agencydesk_test"
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app
from app.database import get_db
from app.auth import hash_password
from app.models import Agency, User, Membership, Client, Project, ProjectMembership, Task, Role, Visibility, TaskStatus, TaskPriority

engine = create_engine(os.environ["DATABASE_URL"])
TestingSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE UNIQUE INDEX uq_invite_pending_per_agency_email "
            "ON invites (agency_id, email) WHERE status = 'pending'"
        ))
        conn.commit()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seeded(setup_db):
    """Two agencies, each with an admin + a client, one client-visible and
    one internal task in each -- the minimum shape needed to prove
    cross-tenant isolation and visibility rules."""
    db = TestingSessionLocal()

    a1 = Agency(name="Agency One", slug="agency-one")
    a2 = Agency(name="Agency Two", slug="agency-two")
    db.add_all([a1, a2]); db.flush()

    admin1 = User(email="admin1@test.com", hashed_password=hash_password("pw"), name="Admin1")
    admin2 = User(email="admin2@test.com", hashed_password=hash_password("pw"), name="Admin2")
    db.add_all([admin1, admin2]); db.flush()
    db.add(Membership(user_id=admin1.id, agency_id=a1.id, role=Role.agency_admin))
    db.add(Membership(user_id=admin2.id, agency_id=a2.id, role=Role.agency_admin))
    db.flush()

    c1 = Client(agency_id=a1.id, name="Client One")
    c2 = Client(agency_id=a2.id, name="Client Two")
    db.add_all([c1, c2]); db.flush()

    client_user1 = User(email="client1@test.com", hashed_password=hash_password("pw"), name="ClientUser1")
    db.add(client_user1); db.flush()
    db.add(Membership(user_id=client_user1.id, agency_id=a1.id, role=Role.client_user, client_id=c1.id))
    db.flush()

    p1 = Project(agency_id=a1.id, client_id=c1.id, name="Project One")
    p2 = Project(agency_id=a2.id, client_id=c2.id, name="Project Two")
    db.add_all([p1, p2]); db.flush()

    t1_internal = Task(agency_id=a1.id, project_id=p1.id, title="Internal task A1",
                        visibility=Visibility.internal, status=TaskStatus.todo, priority=TaskPriority.medium)
    t1_visible = Task(agency_id=a1.id, project_id=p1.id, title="Client-visible task A1",
                       visibility=Visibility.client_visible, status=TaskStatus.todo, priority=TaskPriority.medium)
    t2_internal = Task(agency_id=a2.id, project_id=p2.id, title="Internal task A2",
                        visibility=Visibility.internal, status=TaskStatus.todo, priority=TaskPriority.medium)
    db.add_all([t1_internal, t1_visible, t2_internal]); db.flush()

    db.commit()

    data = {
        "a1": a1.id, "a2": a2.id,
        "admin1": admin1.id, "admin2": admin2.id,
        "c1": c1.id, "c2": c2.id,
        "client_user1": client_user1.id,
        "p1": p1.id, "p2": p2.id,
        "t1_internal": t1_internal.id, "t1_visible": t1_visible.id, "t2_internal": t2_internal.id,
    }
    db.close()
    return data


def login_and_get_token(client, email, password="pw"):
    login = client.post("/auth/login", json={"email": email, "password": password}).json()
    membership_id = login["memberships"][0]["membership_id"]
    sel = client.post("/auth/select-agency", json={
        "identity_token": login["identity_token"], "membership_id": membership_id,
    }).json()
    return sel["access_token"]
