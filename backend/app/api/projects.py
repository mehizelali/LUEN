import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import (
    ActivityEvent,
    Label,
    Organization,
    OrgMembership,
    Project,
    ProjectMembership,
    ProjectStatus,
    User,
    WorkItem,
)
from app.schemas import (
    ActivityOut,
    AdminDashboardOut,
    DashboardOut,
    OrgMemberOut,
    OverdueItem,
    ProjectCreate,
    ProjectMemberAdd,
    ProjectOut,
    ProjectStatusOut,
    SeriesPoint,
    UserOut,
    WorkloadRow,
)
from app.services.activity import log_activity
from app.services.rbac import (
    get_org_membership,
    get_role,
    require_org_member,
    require_permission,
    require_project_access,
)

router = APIRouter(tags=["projects"])

DEFAULT_STATUSES = [
    ("backlog", "Backlog", "backlog", 0),
    ("todo", "To Do", "backlog", 1),
    ("in_progress", "In Progress", "started", 2),
    ("review", "Review", "started", 3),
    ("done", "Done", "done", 4),
]

DEFAULT_LABELS = [
    ("bug", "#E4572E"),
    ("feature", "#2E86AB"),
    ("chore", "#6C757D"),
]


@router.post("/orgs/{org_id}/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    org_id: uuid.UUID,
    body: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    require_permission(db, user.id, "project:create", org_id=org_id)
    if not db.get(Organization, org_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    existing = db.scalar(select(Project).where(Project.org_id == org_id, Project.key == body.key))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Project key already exists in org")

    project = Project(
        org_id=org_id,
        name=body.name,
        key=body.key.upper(),
        description=body.description,
        created_by=user.id,
    )
    db.add(project)
    db.flush()

    for key, name, category, position in DEFAULT_STATUSES:
        db.add(
            ProjectStatus(
                project_id=project.id, key=key, name=name, category=category, position=position
            )
        )
    for name, color in DEFAULT_LABELS:
        db.add(Label(project_id=project.id, name=name, color=color))

    admin_role = get_role(db, "project", "project_admin")
    db.add(ProjectMembership(project_id=project.id, user_id=user.id, role_id=admin_role.id))

    log_activity(
        db,
        org_id=org_id,
        project_id=project.id,
        actor_id=user.id,
        entity_type="project",
        entity_id=project.id,
        action="created",
        payload={"name": project.name, "key": project.key},
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("/orgs/{org_id}/projects", response_model=list[ProjectOut])
def list_projects(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Project]:
    require_org_member(db, user.id, org_id)
    require_permission(db, user.id, "project:view", org_id=org_id)
    projects = db.scalars(
        select(Project).where(Project.org_id == org_id, Project.status == "active").order_by(Project.name)
    ).all()
    # Filter to projects user can view (org elevated already has project:view via elevation).
    visible: list[Project] = []
    for p in projects:
        try:
            require_project_access(db, user.id, p)
            visible.append(p)
        except HTTPException:
            continue
    return visible


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    require_project_access(db, user.id, project)
    return project


@router.get("/projects/{project_id}/statuses", response_model=list[ProjectStatusOut])
def list_statuses(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProjectStatus]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    require_project_access(db, user.id, project)
    return list(
        db.scalars(
            select(ProjectStatus)
            .where(ProjectStatus.project_id == project_id)
            .order_by(ProjectStatus.position)
        ).all()
    )


@router.post("/projects/{project_id}/members", status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: uuid.UUID,
    body: ProjectMemberAdd,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    require_permission(db, user.id, "project:manage", org_id=project.org_id, project_id=project.id)
    if body.role_key not in {"project_admin", "project_member", "project_viewer"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid role_key")
    require_org_member(db, body.user_id, project.org_id)
    role = get_role(db, "project", body.role_key)
    existing = db.scalar(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project_id, ProjectMembership.user_id == body.user_id
        )
    )
    if existing:
        existing.role_id = role.id
    else:
        db.add(ProjectMembership(project_id=project_id, user_id=body.user_id, role_id=role.id))
    db.commit()
    return {"ok": True}


def _project_stats(db: Session, projects: list[Project]) -> list[dict]:
    project_stats = []
    for p in projects:
        total = db.scalar(select(func.count()).select_from(WorkItem).where(WorkItem.project_id == p.id)) or 0
        done_ids = select(ProjectStatus.id).where(
            ProjectStatus.project_id == p.id, ProjectStatus.category == "done"
        )
        done = (
            db.scalar(
                select(func.count())
                .select_from(WorkItem)
                .where(WorkItem.project_id == p.id, WorkItem.status_id.in_(done_ids))
            )
            or 0
        )
        open_count = total - done
        project_stats.append(
            {
                "id": str(p.id),
                "name": p.name,
                "key": p.key,
                "total": total,
                "done": done,
                "open": open_count,
            }
        )
    return project_stats


def _my_open_tasks(db: Session, org_id: uuid.UUID, user_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(WorkItem)
            .join(Project, Project.id == WorkItem.project_id)
            .outerjoin(ProjectStatus, ProjectStatus.id == WorkItem.status_id)
            .where(
                Project.org_id == org_id,
                WorkItem.assignee_id == user_id,
                (ProjectStatus.category.is_(None)) | (ProjectStatus.category != "done"),
            )
        )
        or 0
    )


@router.get("/orgs/{org_id}/dashboard", response_model=DashboardOut)
def dashboard(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardOut:
    membership = require_org_member(db, user.id, org_id)
    membership = get_org_membership(db, user.id, org_id)
    assert membership is not None
    projects = list_projects(org_id, db, user)
    role_key = membership.role.key
    return DashboardOut(
        my_open_tasks=_my_open_tasks(db, org_id, user.id),
        projects=_project_stats(db, projects),
        role_key=role_key,
        is_admin=role_key in {"org_owner", "org_admin"},
    )


@router.get("/orgs/{org_id}/admin-dashboard", response_model=AdminDashboardOut)
def admin_dashboard(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AdminDashboardOut:
    """Org owner/admin overview: KPIs, workload, overdue, activity, members."""
    require_permission(db, user.id, "org:invite", org_id=org_id)
    membership = get_org_membership(db, user.id, org_id)
    assert membership is not None
    role_key = membership.role.key

    projects = list(
        db.scalars(
            select(Project).where(Project.org_id == org_id, Project.status == "active").order_by(Project.name)
        ).all()
    )
    project_ids = [p.id for p in projects]
    project_stats = _project_stats(db, projects)

    members = db.scalars(
        select(OrgMembership)
        .options(selectinload(OrgMembership.user), selectinload(OrgMembership.role))
        .where(OrgMembership.org_id == org_id)
    ).all()

    total_tasks = 0
    done_tasks = 0
    if project_ids:
        total_tasks = (
            db.scalar(select(func.count()).select_from(WorkItem).where(WorkItem.project_id.in_(project_ids)))
            or 0
        )
        done_tasks = (
            db.scalar(
                select(func.count())
                .select_from(WorkItem)
                .join(ProjectStatus, ProjectStatus.id == WorkItem.status_id)
                .where(WorkItem.project_id.in_(project_ids), ProjectStatus.category == "done")
            )
            or 0
        )
    open_tasks = total_tasks - done_tasks

    unassigned = 0
    if project_ids:
        unassigned = (
            db.scalar(
                select(func.count())
                .select_from(WorkItem)
                .outerjoin(ProjectStatus, ProjectStatus.id == WorkItem.status_id)
                .where(
                    WorkItem.project_id.in_(project_ids),
                    WorkItem.assignee_id.is_(None),
                    (ProjectStatus.category.is_(None)) | (ProjectStatus.category != "done"),
                )
            )
            or 0
        )

    now = datetime.now(UTC)
    overdue_rows: list[OverdueItem] = []
    if project_ids:
        overdue_items = db.scalars(
            select(WorkItem)
            .options(selectinload(WorkItem.assignee))
            .join(Project, Project.id == WorkItem.project_id)
            .outerjoin(ProjectStatus, ProjectStatus.id == WorkItem.status_id)
            .where(
                WorkItem.project_id.in_(project_ids),
                WorkItem.due_at.is_not(None),
                WorkItem.due_at < now,
                (ProjectStatus.category.is_(None)) | (ProjectStatus.category != "done"),
            )
            .order_by(WorkItem.due_at)
            .limit(20)
        ).all()
        project_by_id = {p.id: p for p in projects}
        for item in overdue_items:
            proj = project_by_id.get(item.project_id)
            overdue_rows.append(
                OverdueItem(
                    id=item.id,
                    project_id=item.project_id,
                    project_key=proj.key if proj else "?",
                    number=item.number,
                    title=item.title,
                    priority=item.priority,
                    due_at=item.due_at,
                    assignee_name=item.assignee.name if item.assignee else None,
                )
            )

    by_priority = {"low": 0, "medium": 0, "high": 0, "urgent": 0}
    by_category = {"backlog": 0, "started": 0, "done": 0}
    workload: list[WorkloadRow] = []
    if project_ids:
        all_items = db.scalars(
            select(WorkItem)
            .options(selectinload(WorkItem.assignee), selectinload(WorkItem.status))
            .where(WorkItem.project_id.in_(project_ids))
        ).all()
        buckets: dict[uuid.UUID, WorkloadRow] = {}
        for item in all_items:
            category = item.status.category if item.status else "backlog"
            by_category[category] = by_category.get(category, 0) + 1
            is_done = category == "done"
            if not is_done:
                by_priority[item.priority] = by_priority.get(item.priority, 0) + 1
            if item.assignee_id and item.assignee:
                row = buckets.get(item.assignee_id)
                if not row:
                    row = WorkloadRow(
                        user_id=item.assignee_id,
                        name=item.assignee.name,
                        email=item.assignee.email,
                        open_tasks=0,
                        done_tasks=0,
                    )
                    buckets[item.assignee_id] = row
                if is_done:
                    row.done_tasks += 1
                else:
                    row.open_tasks += 1
        workload = sorted(buckets.values(), key=lambda r: r.open_tasks, reverse=True)
        if unassigned:
            workload.insert(
                0,
                WorkloadRow(
                    user_id=None,
                    name="Unassigned",
                    email=None,
                    open_tasks=unassigned,
                    done_tasks=0,
                ),
            )

    events = db.scalars(
        select(ActivityEvent)
        .where(ActivityEvent.org_id == org_id)
        .order_by(ActivityEvent.created_at.desc())
        .limit(25)
    ).all()

    # 14-day activity timeseries for plots
    days = 14
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    hist_events = db.scalars(
        select(ActivityEvent).where(
            ActivityEvent.org_id == org_id, ActivityEvent.created_at >= start
        )
    ).all()
    buckets_ts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"created": 0, "updated": 0, "commented": 0, "total": 0}
    )
    for ev in hist_events:
        day = ev.created_at.astimezone(UTC).date().isoformat()
        buckets_ts[day]["total"] += 1
        if ev.action == "created":
            buckets_ts[day]["created"] += 1
        elif ev.action == "commented":
            buckets_ts[day]["commented"] += 1
        else:
            buckets_ts[day]["updated"] += 1

    activity_series: list[SeriesPoint] = []
    for i in range(days):
        day = (start + timedelta(days=i)).date().isoformat()
        row = buckets_ts.get(day, {"created": 0, "updated": 0, "commented": 0, "total": 0})
        activity_series.append(
            SeriesPoint(
                date=day,
                created=row["created"],
                updated=row["updated"],
                commented=row["commented"],
                total=row["total"],
            )
        )

    completion_rate = round((done_tasks / total_tasks) * 100, 1) if total_tasks else 0.0
    overdue_rate = round((len(overdue_rows) / open_tasks) * 100, 1) if open_tasks else 0.0
    unassigned_rate = round((unassigned / open_tasks) * 100, 1) if open_tasks else 0.0
    # Simple risk index 0-100: overdue + unassigned + urgent/high pressure
    urgent_open = by_priority.get("urgent", 0) + by_priority.get("high", 0)
    pressure = (urgent_open / open_tasks) if open_tasks else 0.0
    risk_index = int(
        min(
            100,
            round(
                overdue_rate * 0.45
                + unassigned_rate * 0.25
                + pressure * 100 * 0.30
            ),
        )
    )
    throughput_14d = sum(1 for e in hist_events if e.action == "created" and e.entity_type == "work_item")
    active_contributors = len([w for w in workload if w.user_id and w.open_tasks + w.done_tasks > 0])

    project_breakdown = [
        {
            "key": p["key"],
            "name": p["name"],
            "open": p["open"],
            "done": p["done"],
            "total": p["total"],
            "completion_pct": round((p["done"] / p["total"]) * 100, 1) if p["total"] else 0.0,
        }
        for p in project_stats
    ]

    return AdminDashboardOut(
        role_key=role_key,
        is_admin=True,
        summary={
            "members": len(members),
            "projects": len(projects),
            "total_tasks": total_tasks,
            "open_tasks": open_tasks,
            "done_tasks": done_tasks,
            "unassigned_open": unassigned,
            "overdue": len(overdue_rows),
        },
        kpis={
            "completion_rate": completion_rate,
            "overdue_rate": overdue_rate,
            "unassigned_rate": unassigned_rate,
            "risk_index": risk_index,
            "throughput_14d": throughput_14d,
            "active_contributors": active_contributors,
            "avg_open_per_contributor": round(open_tasks / active_contributors, 1)
            if active_contributors
            else float(open_tasks),
        },
        by_priority=by_priority,
        by_category=by_category,
        projects=project_stats,
        workload=workload,
        overdue=overdue_rows,
        recent_activity=[ActivityOut.model_validate(e) for e in events],
        members=[
            OrgMemberOut(
                user=UserOut.model_validate(m.user),
                role_key=m.role.key,
                status=m.status,
            )
            for m in members
        ],
        my_open_tasks=_my_open_tasks(db, org_id, user.id),
        activity_series=activity_series,
        project_breakdown=project_breakdown,
    )
