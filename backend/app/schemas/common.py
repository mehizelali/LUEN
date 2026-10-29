import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=2, max_length=128, pattern=r"^[a-z0-9-]+$")


class OrgOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}


class OrgMemberOut(BaseModel):
    user: UserOut
    role_key: str
    status: str


class InviteCreate(BaseModel):
    email: EmailStr
    role_key: str = "org_member"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    key: str = Field(min_length=2, max_length=16, pattern=r"^[A-Z][A-Z0-9]*$")
    description: str | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    key: str
    description: str | None
    status: str

    model_config = {"from_attributes": True}


class ProjectMemberAdd(BaseModel):
    user_id: uuid.UUID
    role_key: str = "project_member"


class ProjectStatusOut(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    category: str
    position: int

    model_config = {"from_attributes": True}


class LabelOut(BaseModel):
    id: uuid.UUID
    name: str
    color: str | None

    model_config = {"from_attributes": True}


class WorkItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    status_id: uuid.UUID | None = None
    priority: str = "medium"
    assignee_id: uuid.UUID | None = None
    due_at: datetime | None = None
    label_ids: list[uuid.UUID] = []


class WorkItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status_id: uuid.UUID | None = None
    priority: str | None = None
    assignee_id: uuid.UUID | None = None
    due_at: datetime | None = None
    label_ids: list[uuid.UUID] | None = None


class WorkItemOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    number: int
    title: str
    description: str | None
    status_id: uuid.UUID | None
    priority: str
    assignee_id: uuid.UUID | None
    reporter_id: uuid.UUID | None
    due_at: datetime | None
    labels: list[LabelOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    body: str = Field(min_length=1)


class CommentOut(BaseModel):
    id: uuid.UUID
    work_item_id: uuid.UUID
    author: UserOut
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    entity_type: str
    entity_id: uuid.UUID | None
    action: str
    payload: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    my_open_tasks: int
    projects: list[dict]
    role_key: str | None = None
    is_admin: bool = False


class WorkloadRow(BaseModel):
    user_id: uuid.UUID | None = None
    name: str
    email: str | None = None
    open_tasks: int
    done_tasks: int


class OverdueItem(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_key: str
    number: int
    title: str
    priority: str
    due_at: datetime
    assignee_name: str | None = None


class SeriesPoint(BaseModel):
    date: str
    created: int = 0
    updated: int = 0
    commented: int = 0
    total: int = 0


class AdminDashboardOut(BaseModel):
    role_key: str
    is_admin: bool
    summary: dict
    kpis: dict
    by_priority: dict[str, int]
    by_category: dict[str, int]
    projects: list[dict]
    workload: list[WorkloadRow]
    overdue: list[OverdueItem]
    recent_activity: list[ActivityOut]
    members: list[OrgMemberOut]
    my_open_tasks: int
    activity_series: list[SeriesPoint] = []
    project_breakdown: list[dict] = []
