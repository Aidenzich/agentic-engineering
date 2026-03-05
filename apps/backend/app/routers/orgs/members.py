from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import (
    AppException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.deps.rbac import require_org_role
from app.models.org import OrgMember, OrgRole, User
from app.schemas.auth import UserResponse
from app.schemas.common import DataResponse
from app.schemas.org import InviteMemberRequest, OrgMemberResponse, UpdateRoleRequest

router = APIRouter(prefix="/api/v1/orgs/{org_id}/members", tags=["org-members"])


def _member_to_response(m: OrgMember) -> OrgMemberResponse:
    return OrgMemberResponse(
        id=m.id,
        user=UserResponse.model_validate(m.user),
        role=m.role,
        joined_at=m.joined_at,
    )


# ---------- GET /orgs/{org_id}/members ----------

@router.get("")
async def list_members(
    org_id: str,
    member: OrgMember = Depends(require_org_role(OrgRole.OWNER, OrgRole.ADMIN, OrgRole.MEMBER)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[OrgMemberResponse]]:
    result = await db.execute(
        select(OrgMember)
        .options(selectinload(OrgMember.user))
        .where(OrgMember.org_id == org_id)
        .order_by(OrgMember.joined_at)
    )
    members = result.scalars().all()
    return DataResponse(data=[_member_to_response(m) for m in members])


# ---------- POST /orgs/{org_id}/members/invite ----------

@router.post("/invite", status_code=201)
async def invite_member(
    org_id: str,
    body: InviteMemberRequest,
    member: OrgMember = Depends(require_org_role(OrgRole.ADMIN, OrgRole.OWNER)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[OrgMemberResponse]:
    # Find user by email
    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise AppException(
            status_code=404,
            code="USER_NOT_FOUND",
            message="User not registered",
        )

    # Check if already a member
    existing = await db.execute(
        select(OrgMember).where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictException(
            code="ALREADY_MEMBER", message="User is already a member of this organization"
        )

    new_member = OrgMember(org_id=org_id, user_id=user.id, role=body.role)
    db.add(new_member)
    await db.flush()

    # Eagerly load user for response
    result = await db.execute(
        select(OrgMember)
        .options(selectinload(OrgMember.user))
        .where(OrgMember.id == new_member.id)
    )
    new_member = result.scalar_one()

    return DataResponse(data=_member_to_response(new_member))


# ---------- PATCH /orgs/{org_id}/members/{user_id}/role ----------

@router.patch("/{user_id}/role")
async def update_member_role(
    org_id: str,
    user_id: str,
    body: UpdateRoleRequest,
    member: OrgMember = Depends(require_org_role(OrgRole.ADMIN, OrgRole.OWNER)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[OrgMemberResponse]:
    # Find the target member
    result = await db.execute(
        select(OrgMember)
        .options(selectinload(OrgMember.user))
        .where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundException("member", user_id)

    # Cannot demote the only OWNER
    if target.role == OrgRole.OWNER and body.role != OrgRole.OWNER:
        owner_count = await db.execute(
            select(func.count())
            .select_from(OrgMember)
            .where(OrgMember.org_id == org_id, OrgMember.role == OrgRole.OWNER)
        )
        if owner_count.scalar_one() <= 1:
            raise ForbiddenException("Cannot demote the only owner of the organization")

    target.role = body.role
    await db.flush()

    return DataResponse(data=_member_to_response(target))


# ---------- DELETE /orgs/{org_id}/members/{user_id} ----------

@router.delete("/{user_id}", status_code=204)
async def remove_member(
    org_id: str,
    user_id: str,
    member: OrgMember = Depends(require_org_role(OrgRole.ADMIN, OrgRole.OWNER)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrgMember).where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == user_id,
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundException("member", user_id)

    if target.role == OrgRole.OWNER:
        raise ForbiddenException("Cannot remove an owner from the organization")

    await db.delete(target)
    await db.flush()

    return Response(status_code=204)
