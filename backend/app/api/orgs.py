import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Invitation, Organization, OrgMembership, User
from app.schemas import InviteCreate, OrgCreate, OrgMemberOut, OrgOut, UserOut
from app.services.activity import log_activity
from app.services.rbac import get_role, require_org_member, require_permission

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.post("", response_model=OrgOut, status_code=status.HTTP_201_CREATED)
def create_org(
    body: OrgCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Organization:
    exists = db.scalar(select(Organization).where(Organization.slug == body.slug))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug already taken")
    org = Organization(name=body.name, slug=body.slug, created_by=user.id)
    db.add(org)
    db.flush()
    owner_role = get_role(db, "org", "org_owner")
    db.add(OrgMembership(org_id=org.id, user_id=user.id, role_id=owner_role.id, status="active"))
    log_activity(
        db,
        org_id=org.id,
        actor_id=user.id,
        entity_type="organization",
        entity_id=org.id,
        action="created",
        payload={"name": org.name},
    )
    db.commit()
    db.refresh(org)
    return org


@router.get("", response_model=list[OrgOut])
def list_orgs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Organization]:
    rows = db.scalars(
        select(Organization)
        .join(OrgMembership, OrgMembership.org_id == Organization.id)
        .where(OrgMembership.user_id == user.id, OrgMembership.status == "active")
        .order_by(Organization.name)
    ).all()
    return list(rows)


@router.get("/{org_id}", response_model=OrgOut)
def get_org(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Organization:
    require_org_member(db, user.id, org_id)
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    return org


@router.get("/{org_id}/members", response_model=list[OrgMemberOut])
def list_members(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[OrgMemberOut]:
    require_permission(db, user.id, "org:view", org_id=org_id)
    memberships = db.scalars(
        select(OrgMembership)
        .options(selectinload(OrgMembership.user), selectinload(OrgMembership.role))
        .where(OrgMembership.org_id == org_id)
    ).all()
    return [
        OrgMemberOut(
            user=UserOut.model_validate(m.user),
            role_key=m.role.key,
            status=m.status,
        )
        for m in memberships
    ]


@router.post("/{org_id}/invitations", status_code=status.HTTP_201_CREATED)
def invite_member(
    org_id: uuid.UUID,
    body: InviteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    require_permission(db, user.id, "org:invite", org_id=org_id)
    if body.role_key not in {"org_admin", "org_member", "org_viewer"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid role_key")
    role = get_role(db, "org", body.role_key)
    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        org_id=org_id,
        email=body.email.lower(),
        role_id=role.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(invitation)
    log_activity(
        db,
        org_id=org_id,
        actor_id=user.id,
        entity_type="invitation",
        entity_id=invitation.id,
        action="created",
        payload={"email": body.email.lower(), "role": body.role_key},
    )
    db.commit()
    # Dev-friendly: return token so UI/tests can accept without email.
    return {"id": str(invitation.id), "token": token, "email": body.email.lower()}
