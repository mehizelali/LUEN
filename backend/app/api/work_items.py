import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import ActivityEvent, Comment, Label, Project, ProjectStatus, User, WorkItem
from app.schemas import (
    ActivityOut,
    CommentCreate,
    CommentOut,
    WorkItemCreate,
    WorkItemOut,
    WorkItemUpdate,
)
from app.services.activity import log_activity
from app.services.rbac import require_permission, require_project_access

router = APIRouter(tags=["work-items"])


def _get_project_or_404(db: Session, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


def _serialize_item(item: WorkItem) -> WorkItemOut:
    return WorkItemOut.model_validate(item)


@router.get("/projects/{project_id}/work-items", response_model=list[WorkItemOut])
def list_work_items(
    project_id: uuid.UUID,
    status_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    label_id: uuid.UUID | None = None,
    q: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[WorkItemOut]:
    project = _get_project_or_404(db, project_id)
    require_project_access(db, user.id, project)
    require_permission(db, user.id, "task:view", org_id=project.org_id, project_id=project.id)

    stmt = (
        select(WorkItem)
        .options(selectinload(WorkItem.labels), selectinload(WorkItem.status))
        .where(WorkItem.project_id == project_id)
        .order_by(WorkItem.number.desc())
    )
    if status_id:
        stmt = stmt.where(WorkItem.status_id == status_id)
    if assignee_id:
        stmt = stmt.where(WorkItem.assignee_id == assignee_id)
    if label_id:
        stmt = stmt.where(WorkItem.labels.any(Label.id == label_id))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(WorkItem.title.ilike(like) | WorkItem.description.ilike(like))
    return [_serialize_item(i) for i in db.scalars(stmt).all()]


@router.post(
    "/projects/{project_id}/work-items",
    response_model=WorkItemOut,
    status_code=status.HTTP_201_CREATED,
)
def create_work_item(
    project_id: uuid.UUID,
    body: WorkItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkItemOut:
    project = _get_project_or_404(db, project_id)
    require_permission(db, user.id, "task:create", org_id=project.org_id, project_id=project.id)

    status_id = body.status_id
    if not status_id:
        first = db.scalar(
            select(ProjectStatus)
            .where(ProjectStatus.project_id == project_id)
            .order_by(ProjectStatus.position)
        )
        status_id = first.id if first else None
    elif not db.scalar(
        select(ProjectStatus).where(ProjectStatus.id == status_id, ProjectStatus.project_id == project_id)
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status_id")

    next_number = (
        db.scalar(select(func.coalesce(func.max(WorkItem.number), 0)).where(WorkItem.project_id == project_id))
        or 0
    ) + 1

    item = WorkItem(
        project_id=project_id,
        number=next_number,
        title=body.title,
        description=body.description,
        status_id=status_id,
        priority=body.priority,
        assignee_id=body.assignee_id,
        reporter_id=user.id,
        due_at=body.due_at,
    )
    if body.label_ids:
        labels = list(
            db.scalars(
                select(Label).where(Label.project_id == project_id, Label.id.in_(body.label_ids))
            ).all()
        )
        item.labels = labels

    db.add(item)
    db.flush()
    log_activity(
        db,
        org_id=project.org_id,
        project_id=project.id,
        actor_id=user.id,
        entity_type="work_item",
        entity_id=item.id,
        action="created",
        payload={"number": item.number, "title": item.title},
    )
    db.commit()
    item = db.scalar(
        select(WorkItem).options(selectinload(WorkItem.labels)).where(WorkItem.id == item.id)
    )
    assert item is not None
    return _serialize_item(item)


@router.get("/work-items/{item_id}", response_model=WorkItemOut)
def get_work_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkItemOut:
    item = db.scalar(
        select(WorkItem).options(selectinload(WorkItem.labels)).where(WorkItem.id == item_id)
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Work item not found")
    project = _get_project_or_404(db, item.project_id)
    require_project_access(db, user.id, project)
    return _serialize_item(item)


@router.patch("/work-items/{item_id}", response_model=WorkItemOut)
def update_work_item(
    item_id: uuid.UUID,
    body: WorkItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkItemOut:
    item = db.scalar(
        select(WorkItem).options(selectinload(WorkItem.labels)).where(WorkItem.id == item_id)
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Work item not found")
    project = _get_project_or_404(db, item.project_id)
    require_permission(db, user.id, "task:edit", org_id=project.org_id, project_id=project.id)

    changes: dict = {}
    data = body.model_dump(exclude_unset=True)
    if "label_ids" in data:
        label_ids = data.pop("label_ids") or []
        labels = list(
            db.scalars(
                select(Label).where(Label.project_id == project.id, Label.id.in_(label_ids))
            ).all()
        )
        item.labels = labels
        changes["label_ids"] = [str(x) for x in label_ids]

    if "assignee_id" in data:
        require_permission(db, user.id, "task:assign", org_id=project.org_id, project_id=project.id)

    if "status_id" in data and data["status_id"] is not None:
        ok = db.scalar(
            select(ProjectStatus).where(
                ProjectStatus.id == data["status_id"], ProjectStatus.project_id == project.id
            )
        )
        if not ok:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status_id")

    for key, value in data.items():
        setattr(item, key, value)
        changes[key] = str(value) if value is not None else None

    log_activity(
        db,
        org_id=project.org_id,
        project_id=project.id,
        actor_id=user.id,
        entity_type="work_item",
        entity_id=item.id,
        action="updated",
        payload=changes,
    )
    db.commit()
    item = db.scalar(
        select(WorkItem).options(selectinload(WorkItem.labels)).where(WorkItem.id == item_id)
    )
    assert item is not None
    return _serialize_item(item)


@router.delete("/work-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    item = db.get(WorkItem, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Work item not found")
    project = _get_project_or_404(db, item.project_id)
    require_permission(db, user.id, "task:delete", org_id=project.org_id, project_id=project.id)
    log_activity(
        db,
        org_id=project.org_id,
        project_id=project.id,
        actor_id=user.id,
        entity_type="work_item",
        entity_id=item.id,
        action="deleted",
        payload={"number": item.number},
    )
    db.delete(item)
    db.commit()


@router.get("/work-items/{item_id}/comments", response_model=list[CommentOut])
def list_comments(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CommentOut]:
    item = db.get(WorkItem, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Work item not found")
    project = _get_project_or_404(db, item.project_id)
    require_project_access(db, user.id, project)
    comments = db.scalars(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.work_item_id == item_id)
        .order_by(Comment.created_at)
    ).all()
    return [CommentOut.model_validate(c) for c in comments]


@router.post(
    "/work-items/{item_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    item_id: uuid.UUID,
    body: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CommentOut:
    item = db.get(WorkItem, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Work item not found")
    project = _get_project_or_404(db, item.project_id)
    require_permission(db, user.id, "comment:create", org_id=project.org_id, project_id=project.id)
    comment = Comment(work_item_id=item_id, author_id=user.id, body=body.body)
    db.add(comment)
    db.flush()
    log_activity(
        db,
        org_id=project.org_id,
        project_id=project.id,
        actor_id=user.id,
        entity_type="work_item",
        entity_id=item.id,
        action="commented",
        payload={"comment_id": str(comment.id)},
    )
    db.commit()
    comment = db.scalar(
        select(Comment).options(selectinload(Comment.author)).where(Comment.id == comment.id)
    )
    assert comment is not None
    return CommentOut.model_validate(comment)


@router.get("/projects/{project_id}/activity", response_model=list[ActivityOut])
def project_activity(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ActivityOut]:
    project = _get_project_or_404(db, project_id)
    require_project_access(db, user.id, project)
    events = db.scalars(
        select(ActivityEvent)
        .where(ActivityEvent.project_id == project_id)
        .order_by(ActivityEvent.created_at.desc())
        .limit(100)
    ).all()
    return [ActivityOut.model_validate(e) for e in events]
