import uuid

from sqlalchemy.orm import Session

from app.models import ActivityEvent


def log_activity(
    db: Session,
    *,
    org_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    entity_type: str,
    entity_id: uuid.UUID | None,
    action: str,
    project_id: uuid.UUID | None = None,
    payload: dict | None = None,
) -> None:
    db.add(
        ActivityEvent(
            org_id=org_id,
            project_id=project_id,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            payload=payload,
        )
    )
