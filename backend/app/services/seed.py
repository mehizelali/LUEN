from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Permission, Role, RolePermission

PERMISSIONS: list[tuple[str, str]] = [
    ("org:manage", "Manage organization settings and ownership"),
    ("org:invite", "Invite members to the organization"),
    ("org:view", "View organization"),
    ("project:create", "Create projects in the organization"),
    ("project:manage", "Manage project settings and members"),
    ("project:view", "View projects"),
    ("task:create", "Create work items"),
    ("task:edit", "Edit work items"),
    ("task:assign", "Assign work items"),
    ("task:delete", "Delete work items"),
    ("task:view", "View work items"),
    ("comment:create", "Create comments"),
    ("attachment:upload", "Upload attachments"),
]

ROLES: list[tuple[str, str, str, list[str]]] = [
    (
        "org",
        "org_owner",
        "Organization Owner",
        [
            "org:manage",
            "org:invite",
            "org:view",
            "project:create",
            "project:manage",
            "project:view",
            "task:create",
            "task:edit",
            "task:assign",
            "task:delete",
            "task:view",
            "comment:create",
            "attachment:upload",
        ],
    ),
    (
        "org",
        "org_admin",
        "Organization Admin",
        [
            "org:invite",
            "org:view",
            "project:create",
            "project:manage",
            "project:view",
            "task:create",
            "task:edit",
            "task:assign",
            "task:delete",
            "task:view",
            "comment:create",
            "attachment:upload",
        ],
    ),
    (
        "org",
        "org_member",
        "Organization Member",
        ["org:view", "project:create", "project:view", "task:view"],
    ),
    ("org", "org_viewer", "Organization Viewer", ["org:view", "project:view", "task:view"]),
    (
        "project",
        "project_admin",
        "Project Admin",
        [
            "project:manage",
            "project:view",
            "task:create",
            "task:edit",
            "task:assign",
            "task:delete",
            "task:view",
            "comment:create",
            "attachment:upload",
        ],
    ),
    (
        "project",
        "project_member",
        "Project Member",
        [
            "project:view",
            "task:create",
            "task:edit",
            "task:assign",
            "task:view",
            "comment:create",
            "attachment:upload",
        ],
    ),
    ("project", "project_viewer", "Project Viewer", ["project:view", "task:view"]),
]


def seed_rbac(db: Session) -> None:
    perm_by_key: dict[str, Permission] = {}
    for key, description in PERMISSIONS:
        existing = db.scalar(select(Permission).where(Permission.key == key))
        if existing:
            perm_by_key[key] = existing
        else:
            perm = Permission(key=key, description=description)
            db.add(perm)
            db.flush()
            perm_by_key[key] = perm

    for scope, key, name, perm_keys in ROLES:
        role = db.scalar(select(Role).where(Role.scope == scope, Role.key == key))
        if not role:
            role = Role(scope=scope, key=key, name=name)
            db.add(role)
            db.flush()

        existing_links = {
            rp.permission_id
            for rp in db.scalars(
                select(RolePermission).where(RolePermission.role_id == role.id)
            ).all()
        }
        for pk in perm_keys:
            perm = perm_by_key[pk]
            if perm.id not in existing_links:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    db.commit()
