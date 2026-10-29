import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import OrgMembership, Project, ProjectMembership, Role

ORG_ELEVATED = {"org_owner", "org_admin"}


def get_role(db: Session, scope: str, key: str) -> Role:
    role = db.scalar(select(Role).where(Role.scope == scope, Role.key == key))
    if not role:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Missing seeded role {scope}:{key}")
    return role


def get_org_membership(db: Session, user_id: uuid.UUID, org_id: uuid.UUID) -> OrgMembership | None:
    return db.scalar(
        select(OrgMembership)
        .options(selectinload(OrgMembership.role).selectinload(Role.permissions))
        .where(
            OrgMembership.user_id == user_id,
            OrgMembership.org_id == org_id,
            OrgMembership.status == "active",
        )
    )


def get_project_membership(
    db: Session, user_id: uuid.UUID, project_id: uuid.UUID
) -> ProjectMembership | None:
    return db.scalar(
        select(ProjectMembership)
        .options(selectinload(ProjectMembership.role).selectinload(Role.permissions))
        .where(ProjectMembership.user_id == user_id, ProjectMembership.project_id == project_id)
    )


def permission_keys_from_role(role: Role | None) -> set[str]:
    if not role:
        return set()
    return {p.key for p in role.permissions}


def collect_permissions(
    db: Session,
    user_id: uuid.UUID,
    *,
    org_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> set[str]:
    perms: set[str] = set()
    resolved_org_id = org_id

    if project_id and not resolved_org_id:
        project = db.get(Project, project_id)
        if project:
            resolved_org_id = project.org_id

    if resolved_org_id:
        org_m = get_org_membership(db, user_id, resolved_org_id)
        if org_m:
            perms |= permission_keys_from_role(org_m.role)
            if org_m.role.key in ORG_ELEVATED:
                # Org admins inherit project admin capabilities.
                admin_role = get_role(db, "project", "project_admin")
                perms |= permission_keys_from_role(admin_role)

    if project_id:
        proj_m = get_project_membership(db, user_id, project_id)
        if proj_m:
            perms |= permission_keys_from_role(proj_m.role)

    return perms


def require_permission(
    db: Session,
    user_id: uuid.UUID,
    permission: str,
    *,
    org_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> None:
    perms = collect_permissions(db, user_id, org_id=org_id, project_id=project_id)
    if permission not in perms:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing permission: {permission}")


def require_org_member(db: Session, user_id: uuid.UUID, org_id: uuid.UUID) -> OrgMembership:
    membership = get_org_membership(db, user_id, org_id)
    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this organization")
    return membership


def require_project_access(db: Session, user_id: uuid.UUID, project: Project) -> set[str]:
    perms = collect_permissions(db, user_id, org_id=project.org_id, project_id=project.id)
    if "project:view" not in perms and "task:view" not in perms:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this project")
    return perms
