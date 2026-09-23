from datetime import date, datetime
from pydantic import BaseModel, EmailStr

from .models import Role, Visibility, TaskStatus, TaskPriority, ApprovalStatus


# ---- auth ----
class SignupAgency(BaseModel):
    agency_name: str
    admin_name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MembershipOption(BaseModel):
    membership_id: str
    agency_id: str
    agency_name: str
    role: Role

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    identity_token: str
    memberships: list[MembershipOption]


class SelectAgencyRequest(BaseModel):
    identity_token: str
    membership_id: str


class TokenResponse(BaseModel):
    access_token: str
    role: Role
    agency_id: str
    agency_name: str


# ---- clients ----
class ClientCreate(BaseModel):
    name: str


class ClientOut(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


# ---- projects ----
class ProjectCreate(BaseModel):
    name: str
    client_id: str


class ProjectOut(BaseModel):
    id: str
    name: str
    client_id: str

    class Config:
        from_attributes = True


# ---- tasks ----
class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.medium
    assignee_user_id: str | None = None
    due_date: date | None = None
    visibility: Visibility = Visibility.internal


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_user_id: str | None = None
    due_date: date | None = None
    visibility: Visibility | None = None


class TaskOut(BaseModel):
    id: str
    project_id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee_user_id: str | None
    due_date: date | None
    visibility: Visibility

    class Config:
        from_attributes = True


# ---- comments ----
class CommentCreate(BaseModel):
    body: str
    visibility: Visibility = Visibility.internal


class CommentOut(BaseModel):
    id: str
    task_id: str
    author_user_id: str
    body: str
    visibility: Visibility
    created_at: datetime

    class Config:
        from_attributes = True


# ---- time entries ----
class TimeEntryCreate(BaseModel):
    duration_minutes: int
    note: str = ""
    entry_date: date


class TimeEntryOut(BaseModel):
    id: str
    task_id: str
    user_id: str
    duration_minutes: int
    note: str
    entry_date: date

    class Config:
        from_attributes = True


# ---- files ----
class FileOut(BaseModel):
    id: str
    task_id: str
    filename: str
    visibility: Visibility
    approval_status: ApprovalStatus

    class Config:
        from_attributes = True


class FileApprovalUpdate(BaseModel):
    approval_status: ApprovalStatus


# ---- invites ----
class InviteCreate(BaseModel):
    email: EmailStr
    role: Role
    client_id: str | None = None


class InviteOut(BaseModel):
    id: str
    email: str
    role: Role
    status: str
    token: str

    class Config:
        from_attributes = True


class InviteAcceptRequest(BaseModel):
    token: str
    name: str
    password: str


# ---- dashboard ----
class ProjectDashboard(BaseModel):
    project_id: str
    task_counts_by_status: dict[str, int]
    total_hours: float
