"""Load rich fake data for local demos.

Usage (from backend/):
  source .venv/bin/activate
  python -m scripts.seed_demo
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    ActivityEvent,
    Attachment,
    Comment,
    Invitation,
    Label,
    Organization,
    OrgMembership,
    Project,
    ProjectMembership,
    ProjectStatus,
    User,
    WorkItem,
    WorkItemLabel,
)
from app.services.rbac import get_role
from app.services.seed import seed_rbac

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
    ("infra", "#5C4B7A"),
    ("docs", "#3CB371"),
]

# Override locally via SEED_PASSWORD — do not commit real prod passwords.
PASSWORD = os.environ.get("SEED_PASSWORD", "secret12")


def wipe_business_data(db) -> None:
    for model in (
        WorkItemLabel,
        Comment,
        Attachment,
        ActivityEvent,
        Invitation,
        WorkItem,
        Label,
        ProjectStatus,
        ProjectMembership,
        Project,
        OrgMembership,
        Organization,
    ):
        db.execute(delete(model))
    db.commit()


def upsert_user(db, email: str, name: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        user.name = name
        user.password_hash = hash_password(PASSWORD)
        user.is_active = True
        return user
    user = User(email=email, name=name, password_hash=hash_password(PASSWORD))
    db.add(user)
    db.flush()
    return user


def add_statuses_and_labels(db, project: Project) -> dict[str, ProjectStatus]:
    statuses: dict[str, ProjectStatus] = {}
    for key, name, category, position in DEFAULT_STATUSES:
        st = ProjectStatus(
            project_id=project.id, key=key, name=name, category=category, position=position
        )
        db.add(st)
        db.flush()
        statuses[key] = st
    for name, color in DEFAULT_LABELS:
        db.add(Label(project_id=project.id, name=name, color=color))
    db.flush()
    return statuses


def create_project(
    db,
    *,
    org: Organization,
    name: str,
    key: str,
    description: str,
    creator: User,
    members: list[tuple[User, str]],
) -> tuple[Project, dict[str, ProjectStatus]]:
    project = Project(
        org_id=org.id,
        name=name,
        key=key,
        description=description,
        created_by=creator.id,
        status="active",
    )
    db.add(project)
    db.flush()
    statuses = add_statuses_and_labels(db, project)
    for member, role_key in members:
        role = get_role(db, "project", role_key)
        db.add(ProjectMembership(project_id=project.id, user_id=member.id, role_id=role.id))
    db.add(
        ActivityEvent(
            org_id=org.id,
            project_id=project.id,
            actor_id=creator.id,
            entity_type="project",
            entity_id=project.id,
            action="created",
            payload={"name": name, "key": key},
        )
    )
    return project, statuses


def add_task(
    db,
    *,
    org: Organization,
    project: Project,
    statuses: dict[str, ProjectStatus],
    number: int,
    title: str,
    description: str,
    status_key: str,
    priority: str,
    reporter: User,
    assignee: User | None,
    due_at: datetime | None,
    labels: list[str] | None = None,
    comments: list[tuple[User, str]] | None = None,
) -> WorkItem:
    item = WorkItem(
        project_id=project.id,
        number=number,
        title=title,
        description=description,
        status_id=statuses[status_key].id,
        priority=priority,
        assignee_id=assignee.id if assignee else None,
        reporter_id=reporter.id,
        due_at=due_at,
    )
    db.add(item)
    db.flush()

    if labels:
        label_rows = db.scalars(
            select(Label).where(Label.project_id == project.id, Label.name.in_(labels))
        ).all()
        item.labels = list(label_rows)

    db.add(
        ActivityEvent(
            org_id=org.id,
            project_id=project.id,
            actor_id=reporter.id,
            entity_type="work_item",
            entity_id=item.id,
            action="created",
            payload={"number": number, "title": title},
        )
    )
    if assignee:
        db.add(
            ActivityEvent(
                org_id=org.id,
                project_id=project.id,
                actor_id=reporter.id,
                entity_type="work_item",
                entity_id=item.id,
                action="assigned",
                payload={"assignee": assignee.email},
            )
        )
    for author, body in comments or []:
        c = Comment(work_item_id=item.id, author_id=author.id, body=body)
        db.add(c)
        db.flush()
        db.add(
            ActivityEvent(
                org_id=org.id,
                project_id=project.id,
                actor_id=author.id,
                entity_type="work_item",
                entity_id=item.id,
                action="commented",
                payload={"comment_id": str(c.id)},
            )
        )
    return item


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_rbac(db)
        wipe_business_data(db)

        owner = upsert_user(db, "owner@example.com", "Amina Owner")
        admin = upsert_user(db, "admin@example.com", "Yacine Admin")
        sara = upsert_user(db, "sara@example.com", "Sara Dev")
        karim = upsert_user(db, "karim@example.com", "Karim Dev")
        lina = upsert_user(db, "lina@example.com", "Lina Designer")
        nabil = upsert_user(db, "nabil@example.com", "Nabil QA")
        viewer = upsert_user(db, "viewer@example.com", "Omar Viewer")
        db.flush()

        acme = Organization(name="Acme Delivery", slug="acme", created_by=owner.id)
        north = Organization(name="Northwind Cloud", slug="northwind", created_by=admin.id)
        db.add_all([acme, north])
        db.flush()

        org_owner = get_role(db, "org", "org_owner")
        org_admin = get_role(db, "org", "org_admin")
        org_member = get_role(db, "org", "org_member")
        org_viewer = get_role(db, "org", "org_viewer")

        for u, role in [
            (owner, org_owner),
            (admin, org_admin),
            (sara, org_member),
            (karim, org_member),
            (lina, org_member),
            (nabil, org_member),
            (viewer, org_viewer),
        ]:
            db.add(OrgMembership(org_id=acme.id, user_id=u.id, role_id=role.id, status="active"))

        db.add(OrgMembership(org_id=north.id, user_id=admin.id, role_id=org_owner.id, status="active"))
        db.add(OrgMembership(org_id=north.id, user_id=sara.id, role_id=org_member.id, status="active"))
        db.add(OrgMembership(org_id=north.id, user_id=owner.id, role_id=org_admin.id, status="active"))

        now = datetime.now(UTC)

        kube, kube_st = create_project(
            db,
            org=acme,
            name="Kube Platform",
            key="KUBE",
            description="Cluster, CI, and platform reliability work",
            creator=owner,
            members=[
                (owner, "project_admin"),
                (admin, "project_admin"),
                (sara, "project_member"),
                (karim, "project_member"),
                (nabil, "project_member"),
                (viewer, "project_viewer"),
            ],
        )
        app, app_st = create_project(
            db,
            org=acme,
            name="Customer Portal",
            key="PORT",
            description="Web app delivery for customer self-service",
            creator=admin,
            members=[
                (admin, "project_admin"),
                (lina, "project_member"),
                (sara, "project_member"),
                (nabil, "project_member"),
                (owner, "project_admin"),
            ],
        )
        ml, ml_st = create_project(
            db,
            org=north,
            name="Inference Service",
            key="INF",
            description="Model serving and observability",
            creator=admin,
            members=[
                (admin, "project_admin"),
                (sara, "project_member"),
                (owner, "project_member"),
            ],
        )

        kube_tasks = [
            (
                "Provision staging cluster",
                "Bring up 3-node k3s staging with ingress and cert-manager.",
                "done",
                "high",
                owner,
                sara,
                now - timedelta(days=10),
                ["infra", "chore"],
                [(sara, "Cluster is green. Ingress smoke tests passed.")],
            ),
            (
                "Harden RBAC for namespaces",
                "Least-privilege roles for app teams; no cluster-admin in CI.",
                "review",
                "urgent",
                admin,
                karim,
                now - timedelta(days=2),
                ["infra"],
                [(karim, "PR ready — need security review."), (admin, "Looking today.")],
            ),
            (
                "Add Prometheus scrape configs",
                "ServiceMonitors for API, workers, and Postgres exporter.",
                "in_progress",
                "high",
                sara,
                sara,
                now + timedelta(days=2),
                ["infra", "feature"],
                [],
            ),
            (
                "Fix CrashLoop on worker pods",
                "OOM after batch import; tune limits and backlog.",
                "in_progress",
                "urgent",
                nabil,
                karim,
                now - timedelta(days=1),
                ["bug", "infra"],
                [(nabil, "Reproduced with 50k import file.")],
            ),
            (
                "Document cluster runbook",
                "On-call steps for node drain, certificate renewals, and rollback.",
                "todo",
                "medium",
                owner,
                None,
                now + timedelta(days=7),
                ["docs"],
                [],
            ),
            (
                "Blue/green deploy for API",
                "Use Argo Rollouts progressive delivery.",
                "todo",
                "high",
                admin,
                sara,
                now + timedelta(days=5),
                ["feature", "infra"],
                [],
            ),
            (
                "Rotate registry credentials",
                "Move to short-lived tokens from vault.",
                "backlog",
                "medium",
                owner,
                None,
                None,
                ["chore", "infra"],
                [],
            ),
            (
                "Cost report for GPU nodes",
                "Weekly export to finance sheet.",
                "backlog",
                "low",
                admin,
                lina,
                now + timedelta(days=14),
                ["chore"],
                [],
            ),
        ]

        for i, (title, desc, st, pri, rep, asg, due, labs, comments) in enumerate(kube_tasks, start=1):
            add_task(
                db,
                org=acme,
                project=kube,
                statuses=kube_st,
                number=i,
                title=title,
                description=desc,
                status_key=st,
                priority=pri,
                reporter=rep,
                assignee=asg,
                due_at=due,
                labels=labs,
                comments=comments,
            )

        portal_tasks = [
            (
                "Redesign login screen",
                "Match new brand; mobile-first.",
                "done",
                "medium",
                lina,
                lina,
                now - timedelta(days=8),
                ["feature", "docs"],
                [(lina, "Shipped in v1.4")],
            ),
            (
                "SSO with Google Workspace",
                "OIDC login for enterprise tenants.",
                "in_progress",
                "high",
                sara,
                sara,
                now + timedelta(days=3),
                ["feature"],
                [(sara, "Callback URL configured in staging.")],
            ),
            (
                "Invoice PDF download broken",
                "500 on invoices older than 90 days.",
                "review",
                "urgent",
                nabil,
                karim,
                now - timedelta(days=3),
                ["bug"],
                [(nabil, "Fails only for archived storage path.")],
            ),
            (
                "Empty state for projects list",
                "Friendly CTA when workspace has no projects.",
                "todo",
                "low",
                lina,
                lina,
                now + timedelta(days=9),
                ["feature"],
                [],
            ),
            (
                "Rate-limit public signup",
                "Protect /register against credential stuffing.",
                "todo",
                "high",
                admin,
                karim,
                now + timedelta(days=4),
                ["chore"],
                [],
            ),
            (
                "Accessibility pass on board",
                "Keyboard nav + contrast AA.",
                "backlog",
                "medium",
                lina,
                None,
                None,
                ["feature"],
                [],
            ),
            (
                "Localization: FR + AR",
                "Extract strings; wire i18n provider.",
                "backlog",
                "medium",
                owner,
                sara,
                now + timedelta(days=21),
                ["feature"],
                [],
            ),
        ]

        for i, (title, desc, st, pri, rep, asg, due, labs, comments) in enumerate(portal_tasks, start=1):
            add_task(
                db,
                org=acme,
                project=app,
                statuses=app_st,
                number=i,
                title=title,
                description=desc,
                status_key=st,
                priority=pri,
                reporter=rep,
                assignee=asg,
                due_at=due,
                labels=labs,
                comments=comments,
            )

        inf_tasks = [
            (
                "GPU autoscaling policy",
                "Scale inference replicas on queue depth.",
                "in_progress",
                "high",
                admin,
                sara,
                now + timedelta(days=1),
                ["infra", "feature"],
                [],
            ),
            (
                "Model warmup latency spike",
                "Cold start > 8s after idle.",
                "todo",
                "urgent",
                sara,
                sara,
                now - timedelta(days=1),
                ["bug"],
                [(sara, "Suspect CUDA context init.")],
            ),
            (
                "Add request tracing",
                "Propagate trace IDs from gateway to workers.",
                "backlog",
                "medium",
                owner,
                None,
                now + timedelta(days=10),
                ["feature"],
                [],
            ),
            (
                "Canary 10% traffic",
                "Route a slice of prod to v2 model.",
                "todo",
                "high",
                admin,
                owner,
                now + timedelta(days=6),
                ["infra"],
                [],
            ),
        ]

        for i, (title, desc, st, pri, rep, asg, due, labs, comments) in enumerate(inf_tasks, start=1):
            add_task(
                db,
                org=north,
                project=ml,
                statuses=ml_st,
                number=i,
                title=title,
                description=desc,
                status_key=st,
                priority=pri,
                reporter=rep,
                assignee=asg,
                due_at=due,
                labels=labs,
                comments=comments,
            )

        db.commit()
        print("Demo data loaded.")
        print("Password for all users:", PASSWORD)
        print("Users: owner@example.com, admin@example.com, sara@example.com,")
        print("       karim@example.com, lina@example.com, nabil@example.com, viewer@example.com")
        print("Orgs: Acme Delivery (/acme), Northwind Cloud (/northwind)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
