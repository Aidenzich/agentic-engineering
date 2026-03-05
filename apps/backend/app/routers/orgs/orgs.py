from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ConflictException
from app.deps.auth import get_current_user
from app.deps.rbac import get_org_member, require_org_role
from app.models.org import OrgMember, OrgRole, Organization, User
from app.schemas.common import DataResponse
from app.schemas.org import OrgCreate, OrgResponse, OrgUpdate

router = APIRouter(prefix="/api/v1/orgs", tags=["orgs"])


# ---------- POST /orgs ----------

@router.post("", status_code=201)
async def create_org(
    body: OrgCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[OrgResponse]:
    # Check slug uniqueness
    existing = await db.execute(
        select(Organization).where(Organization.slug == body.slug)
    )
    if existing.scalar_one_or_none():
        raise ConflictException(
            code="SLUG_EXISTS", message="An organization with this slug already exists"
        )

    org = Organization(name=body.name, slug=body.slug)
    db.add(org)
    await db.flush()

    membership = OrgMember(org_id=org.id, user_id=current_user.id, role=OrgRole.OWNER)
    db.add(membership)
    await db.flush()

    return DataResponse(data=OrgResponse.model_validate(org))


# ---------- GET /orgs ----------

@router.get("")
async def list_orgs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[OrgResponse]]:
    result = await db.execute(
        select(Organization)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .where(OrgMember.user_id == current_user.id)
        .order_by(Organization.created_at.desc())
    )
    orgs = result.scalars().all()
    return DataResponse(data=[OrgResponse.model_validate(o) for o in orgs])


# ---------- GET /orgs/{org_id} ----------

@router.get("/{org_id}")
async def get_org(
    org_id: str,
    member: OrgMember = Depends(get_org_member),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[OrgResponse]:
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one()
    return DataResponse(data=OrgResponse.model_validate(org))


# ---------- PATCH /orgs/{org_id} ----------

@router.patch("/{org_id}")
async def update_org(
    org_id: str,
    body: OrgUpdate,
    member: OrgMember = Depends(require_org_role(OrgRole.ADMIN, OrgRole.OWNER)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[OrgResponse]:
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one()

    if body.name is not None:
        org.name = body.name
    if body.avatar_url is not None:
        org.avatar_url = body.avatar_url
    await db.flush()

    return DataResponse(data=OrgResponse.model_validate(org))
