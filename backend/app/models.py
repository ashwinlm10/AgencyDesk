import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, ForeignKey, ForeignKeyConstraint, UniqueConstraint,
    DateTime, Enum, Text, Date, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Role(str, enum.Enum):
    agency_admin = "agency_admin"
    agency_member = "agency_member"
    client_user = "client_user"


class Visibility(str, enum.Enum):
    internal = "internal"
    client_visible = "client_visible"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    needs_changes = "needs_changes"


class InviteStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    revoked = "revoked"


# ---------------------------------------------------------------------------
# Agency = the tenant. Every other business table carries agency_id and, for
# tables with a parent, a COMPOSITE foreign key (parent_id, agency_id) so the
# database itself refuses to let a row point at a parent from another tenant
# -- this isn't just enforced by app code / query filters.
# ---------------------------------------------------------------------------

class Agency(Base):
    __tablename__ = "agencies"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("id", name="uq_agency_id"),)


class User(Base):
    """Global identity. One row per email, independent of any agency.

    A single user can hold a separate Membership (with its own role) in
    multiple agencies -- that's what lets the same email be a client contact
    for Agency A and a client contact (or even staff) for Agency B.
    """
    __tablename__ = "users"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    memberships = relationship("Membership", back_populates="user")


class Client(Base):
    """A client company that an agency works for."""
    __tablename__ = "clients"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    agency_id = Column(UUID(as_uuid=False), ForeignKey("agencies.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("id", "agency_id", name="uq_client_id_agency"),
        Index("ix_clients_agency", "agency_id"),
    )


class Membership(Base):
    """A user's role inside one specific agency.

    unique(user_id, agency_id) is what makes 'one person, two agencies' safe:
    the same user_id can have at most one row per agency, but as many rows
    as there are agencies. Each row carries its own role independently.
    """
    __tablename__ = "memberships"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    agency_id = Column(UUID(as_uuid=False), ForeignKey("agencies.id"), nullable=False)
    role = Column(Enum(Role), nullable=False)
    # only set when role == client_user: which client company this person represents
    client_id = Column(UUID(as_uuid=False), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("user_id", "agency_id", name="uq_membership_user_agency"),
        UniqueConstraint("id", "agency_id", name="uq_membership_id_agency"),
        UniqueConstraint("user_id", "agency_id", "id", name="uq_membership_lookup"),
        ForeignKeyConstraint(["client_id", "agency_id"], ["clients.id", "clients.agency_id"]),
        Index("ix_memberships_agency", "agency_id"),
    )


class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    agency_id = Column(UUID(as_uuid=False), ForeignKey("agencies.id"), nullable=False)
    client_id = Column(UUID(as_uuid=False), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("id", "agency_id", name="uq_project_id_agency"),
        ForeignKeyConstraint(["client_id", "agency_id"], ["clients.id", "clients.agency_id"]),
        Index("ix_projects_agency", "agency_id"),
    )


class ProjectMembership(Base):
    """Which agency_member/agency_admin users are assigned to a project.
    Drives the 'agency_member sees only assigned projects' rule."""
    __tablename__ = "project_memberships"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    agency_id = Column(UUID(as_uuid=False), ForeignKey("agencies.id"), nullable=False)
    project_id = Column(UUID(as_uuid=False), nullable=False)
    user_id = Column(UUID(as_uuid=False), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_projectmember_once"),
        ForeignKeyConstraint(["project_id", "agency_id"], ["projects.id", "projects.agency_id"]),
        ForeignKeyConstraint(["user_id", "agency_id"], ["memberships.user_id", "memberships.agency_id"]),
        Index("ix_projmem_agency", "agency_id"),
    )


class Task(Base):
    __tablename__ = "tasks"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    agency_id = Column(UUID(as_uuid=False), ForeignKey("agencies.id"), nullable=False)
    project_id = Column(UUID(as_uuid=False), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(Enum(TaskStatus), default=TaskStatus.todo, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.medium, nullable=False)
    assignee_user_id = Column(UUID(as_uuid=False), nullable=True)
    due_date = Column(Date, nullable=True)
    visibility = Column(Enum(Visibility), default=Visibility.internal, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("id", "agency_id", name="uq_task_id_agency"),
        ForeignKeyConstraint(["project_id", "agency_id"], ["projects.id", "projects.agency_id"]),
        ForeignKeyConstraint(
            ["assignee_user_id", "agency_id"],
            ["memberships.user_id", "memberships.agency_id"],
        ),
        Index("ix_tasks_agency", "agency_id"),
        Index("ix_tasks_project", "project_id"),
    )


class Comment(Base):
    __tablename__ = "comments"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    agency_id = Column(UUID(as_uuid=False), ForeignKey("agencies.id"), nullable=False)
    task_id = Column(UUID(as_uuid=False), nullable=False)
    author_user_id = Column(UUID(as_uuid=False), nullable=False)
    body = Column(Text, nullable=False)
    # a comment is client_visible only if a client (or staff replying to them) wrote it
    # visibly; staff can also leave internal-only comments on a client-visible task.
    visibility = Column(Enum(Visibility), default=Visibility.internal, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        ForeignKeyConstraint(["task_id", "agency_id"], ["tasks.id", "tasks.agency_id"]),
        ForeignKeyConstraint(
            ["author_user_id", "agency_id"],
            ["memberships.user_id", "memberships.agency_id"],
        ),
        Index("ix_comments_agency", "agency_id"),
        Index("ix_comments_task", "task_id"),
    )


class TimeEntry(Base):
    __tablename__ = "time_entries"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    agency_id = Column(UUID(as_uuid=False), ForeignKey("agencies.id"), nullable=False)
    task_id = Column(UUID(as_uuid=False), nullable=False)
    user_id = Column(UUID(as_uuid=False), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    note = Column(String, default="")
    entry_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        ForeignKeyConstraint(["task_id", "agency_id"], ["tasks.id", "tasks.agency_id"]),
        ForeignKeyConstraint(
            ["user_id", "agency_id"],
            ["memberships.user_id", "memberships.agency_id"],
        ),
        Index("ix_time_entries_agency", "agency_id"),
        Index("ix_time_entries_task", "task_id"),
    )


class FileAsset(Base):
    __tablename__ = "files"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    agency_id = Column(UUID(as_uuid=False), ForeignKey("agencies.id"), nullable=False)
    task_id = Column(UUID(as_uuid=False), nullable=False)
    uploaded_by_user_id = Column(UUID(as_uuid=False), nullable=False)
    filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    visibility = Column(Enum(Visibility), default=Visibility.internal, nullable=False)
    approval_status = Column(Enum(ApprovalStatus), default=ApprovalStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        ForeignKeyConstraint(["task_id", "agency_id"], ["tasks.id", "tasks.agency_id"]),
        ForeignKeyConstraint(
            ["uploaded_by_user_id", "agency_id"],
            ["memberships.user_id", "memberships.agency_id"],
        ),
        Index("ix_files_agency", "agency_id"),
        Index("ix_files_task", "task_id"),
    )


class Invite(Base):
    """agency_id + email + status='pending' is kept unique at the DB level
    (partial unique index, see migration) so resending an invite can never
    create a second pending row -- the app does an upsert instead."""
    __tablename__ = "invites"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    agency_id = Column(UUID(as_uuid=False), ForeignKey("agencies.id"), nullable=False)
    email = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False)
    client_id = Column(UUID(as_uuid=False), nullable=True)
    token = Column(String, unique=True, nullable=False, default=gen_uuid)
    status = Column(Enum(InviteStatus), default=InviteStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["client_id", "agency_id"], ["clients.id", "clients.agency_id"]),
        Index("ix_invites_agency", "agency_id"),
    )
