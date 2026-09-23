"""Seeds the DB with 2 agencies, staff, a client_user, and a mix of
internal/client-visible tasks -- including one email that's a client contact
for BOTH agencies with different roles, to demonstrate that edge case.

Run: python seed.py   (after `alembic upgrade head`)
"""
import datetime
from app.database import SessionLocal, engine, Base
from app.auth import hash_password
from app.models import (
    Agency, User, Membership, Client, Project, ProjectMembership, Task,
    Comment, TimeEntry, Invite, Visibility, TaskStatus, TaskPriority, Role,
)

Base.metadata.create_all(bind=engine)  # no-op if alembic already ran; safe either way
db = SessionLocal()

PASSWORD = "password123"

# --- Agency 1: Pixel & Pine ---
a1 = Agency(name="Pixel & Pine", slug="pixel-and-pine")
db.add(a1); db.flush()

admin1 = User(email="admin@pixelpine.com", hashed_password=hash_password(PASSWORD), name="Aria (Admin)")
member1 = User(email="member@pixelpine.com", hashed_password=hash_password(PASSWORD), name="Ben (Member)")
db.add_all([admin1, member1]); db.flush()

db.add(Membership(user_id=admin1.id, agency_id=a1.id, role=Role.agency_admin))
db.add(Membership(user_id=member1.id, agency_id=a1.id, role=Role.agency_member))
db.flush()

client1 = Client(agency_id=a1.id, name="Nova Retail Co")
db.add(client1); db.flush()

# The "one person, two agencies" edge case: this email is a client contact
# for Agency 1 AND (further below) a client contact for Agency 2, with a
# different membership row + role each time.
shared_user = User(email="shared@client.com", hashed_password=hash_password(PASSWORD), name="Sam (shared client)")
db.add(shared_user); db.flush()
db.add(Membership(user_id=shared_user.id, agency_id=a1.id, role=Role.client_user, client_id=client1.id))
db.flush()

proj1 = Project(agency_id=a1.id, client_id=client1.id, name="Nova Website Redesign")
db.add(proj1); db.flush()
db.add(ProjectMembership(agency_id=a1.id, project_id=proj1.id, user_id=member1.id))
db.flush()

t1 = Task(agency_id=a1.id, project_id=proj1.id, title="Draft homepage wireframes",
          status=TaskStatus.in_progress, priority=TaskPriority.high,
          assignee_user_id=member1.id, visibility=Visibility.client_visible,
          due_date=datetime.date.today() + datetime.timedelta(days=5))
t2 = Task(agency_id=a1.id, project_id=proj1.id, title="Internal: renegotiate stock photo license",
          status=TaskStatus.todo, priority=TaskPriority.low,
          assignee_user_id=admin1.id, visibility=Visibility.internal)
db.add_all([t1, t2]); db.flush()

db.add(Comment(agency_id=a1.id, task_id=t1.id, author_user_id=member1.id,
               body="First pass is up in Figma, feedback welcome.", visibility=Visibility.client_visible))
db.add(Comment(agency_id=a1.id, task_id=t1.id, author_user_id=admin1.id,
               body="Internal note: client's brand guide is outdated, using new one.", visibility=Visibility.internal))
db.add(TimeEntry(agency_id=a1.id, task_id=t1.id, user_id=member1.id, duration_minutes=180,
                  note="Wireframing", entry_date=datetime.date.today()))
db.flush()

db.add(Invite(agency_id=a1.id, email="new-client@nova.com", role=Role.client_user, client_id=client1.id))

# --- Agency 2: Maple Digital ---
a2 = Agency(name="Maple Digital", slug="maple-digital")
db.add(a2); db.flush()

admin2 = User(email="admin@mapledigital.com", hashed_password=hash_password(PASSWORD), name="Priya (Admin)")
db.add(admin2); db.flush()
db.add(Membership(user_id=admin2.id, agency_id=a2.id, role=Role.agency_admin))

client2 = Client(agency_id=a2.id, name="Orbit Fitness")
db.add(client2); db.flush()

# Same shared_user, different agency, different role -- proves isolation:
# their Agency-1 client_id/role never leaks into this membership.
db.add(Membership(user_id=shared_user.id, agency_id=a2.id, role=Role.client_user, client_id=client2.id))
db.flush()

proj2 = Project(agency_id=a2.id, client_id=client2.id, name="Orbit App Launch Campaign")
db.add(proj2); db.flush()

t3 = Task(agency_id=a2.id, project_id=proj2.id, title="Prep launch day social assets",
          status=TaskStatus.todo, priority=TaskPriority.medium,
          assignee_user_id=admin2.id, visibility=Visibility.client_visible)
db.add(t3); db.flush()

db.commit()

print("Seeded successfully.\n")
print("=== Login credentials (all use password: password123) ===")
print(f"Agency 1 - Pixel & Pine (id={a1.id})")
print("  admin@pixelpine.com   -> agency_admin")
print("  member@pixelpine.com  -> agency_member")
print(f"Agency 2 - Maple Digital (id={a2.id})")
print("  admin@mapledigital.com -> agency_admin")
print("Shared client (client_user in BOTH agencies, different roles/clients):")
print("  shared@client.com  -> log in once, then pick which agency at /auth/select-agency")
db.close()
