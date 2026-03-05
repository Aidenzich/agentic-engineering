import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_db
from app.deps.rbac import require_org_role
from app.events.bus import event_bus
from app.models.org import AuditLog, OrgMember, OrgRole
from app.schemas.common import PaginatedResponse, PaginationMeta

router = APIRouter(prefix="/api/v1/orgs/{org_id}/audit-logs", tags=["audit"])


async def _handle_audit_event(
    org_id: str,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    before: dict | None = None,
    after: dict | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    **kwargs,
) -> None:
    """Write an audit log entry to the DB asynchronously using its own session."""
    async with async_session_factory() as session:
        try:
            log = AuditLog(
                org_id=org_id,
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                before=before,
                after=after,
                metadata_=metadata,
                ip_address=ip_address,
            )
            session.add(log)
            await session.commit()
        except Exception:
            await session.rollback()


def register_audit_handlers() -> None:
    """Register event handlers for audit events on the event bus."""
    event_bus.on("audit.user_registered", _handle_audit_event)
    event_bus.on("audit.org_created", _handle_audit_event)
    event_bus.on("audit.org_updated", _handle_audit_event)
    event_bus.on("audit.member_invited", _handle_audit_event)
    event_bus.on("audit.member_role_changed", _handle_audit_event)
    event_bus.on("audit.member_removed", _handle_audit_event)
    event_bus.on("audit.team_created", _handle_audit_event)
    event_bus.on("audit.team_updated", _handle_audit_event)
    event_bus.on("audit.team_deleted", _handle_audit_event)
    event_bus.on("audit.team_member_added", _handle_audit_event)
    event_bus.on("audit.team_member_removed", _handle_audit_event)


# ---------- GET /orgs/{org_id}/audit-logs ----------

@router.get("")
async def list_audit_logs(
    org_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    member: OrgMember = Depends(require_org_role(OrgRole.ADMIN, OrgRole.OWNER)),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[dict]:
    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.org_id == org_id)
    )
    total = count_result.scalar_one()
    total_pages = math.ceil(total / limit) if total > 0 else 1

    # Fetch page
    offset = (page - 1) * limit
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.org_id == org_id)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    logs = result.scalars().all()

    data = [
        {
            "id": log.id,
            "org_id": log.org_id,
            "actor_id": log.actor_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "before": log.before,
            "after": log.after,
            "metadata": log.metadata_,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]

    return PaginatedResponse(
        data=data,
        meta=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
        ),
    )
