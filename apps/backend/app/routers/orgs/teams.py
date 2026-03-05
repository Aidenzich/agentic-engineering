from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.deps.rbac import get_org_member, require_org_role
from app.models.org import OrgMember, OrgRole, Team, TeamMember, TeamRole, User
from app.schemas.auth import UserResponse
from app.schemas.common import DataResponse
from app.schemas.team import TeamCreate, TeamMemberAdd, TeamResponse, TeamUpdate

router = APIRouter(prefix="/api/v1/orgs/{org_id}/teams", tags=["teams"])


def _team_to_response(team: Team, member_count: int = 0) -> TeamResponse:
    return TeamResponse(
        id=team.id,
        name=team.name,
        slug=team.slug,
        description=team.description,
        created_at=team.created_at,
        member_count=member_count,
    )


async def _get_team_or_404(db: AsyncSession, org_id: str, team_id: str) -> Team:
    result = await db.execute(
        select(Team).where(Team.id == team_id, Team.org_id == org_id)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise NotFoundException("team", team_id)
    return team


async def _is_team_lead(db: AsyncSession, team_id: str, user_id: str) -> bool:
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.role == TeamRole.LEAD,
        )
    )
    return result.scalar_one_or_none() is not None


async def _require_admin_owner_or_lead(
    db: AsyncSession, org_member: OrgMember, team_id: str
) -> None:
    if org_member.role in (OrgRole.ADMIN, OrgRole.OWNER):
        return
    if await _is_team_lead(db, team_id, org_member.user_id):
        return
    raise ForbiddenException("Insufficient role")


async def _count_team_members(db: AsyncSession, team_id: str) -> int:
    result = await db.execute(
        select(func.count()).select_from(TeamMember).where(TeamMember.team_id == team_id)
    )
    return result.scalar_one()


# ---------- GET /orgs/{org_id}/teams ----------

@router.get("")
async def list_teams(
    org_id: str,
    member: OrgMember = Depends(get_org_member),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[TeamResponse]]:
    result = await db.execute(
        select(Team).where(Team.org_id == org_id).order_by(Team.created_at.desc())
    )
    teams = result.scalars().all()

    # Count members for each team
    responses = []
    for team in teams:
        count = await _count_team_members(db, team.id)
        responses.append(_team_to_response(team, count))

    return DataResponse(data=responses)


# ---------- POST /orgs/{org_id}/teams ----------

@router.post("", status_code=201)
async def create_team(
    org_id: str,
    body: TeamCreate,
    member: OrgMember = Depends(require_org_role(OrgRole.ADMIN, OrgRole.OWNER)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[TeamResponse]:
    # Check slug uniqueness within org
    existing = await db.execute(
        select(Team).where(Team.org_id == org_id, Team.slug == body.slug)
    )
    if existing.scalar_one_or_none():
        raise ConflictException(
            code="TEAM_SLUG_EXISTS",
            message="A team with this slug already exists in the organization",
        )

    team = Team(
        org_id=org_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
    )
    db.add(team)
    await db.flush()

    return DataResponse(data=_team_to_response(team, 0))


# ---------- GET /orgs/{org_id}/teams/{team_id} ----------

@router.get("/{team_id}")
async def get_team(
    org_id: str,
    team_id: str,
    member: OrgMember = Depends(get_org_member),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    team = await _get_team_or_404(db, org_id, team_id)

    # Get members with user info
    members_result = await db.execute(
        select(TeamMember)
        .options(selectinload(TeamMember.user))
        .where(TeamMember.team_id == team_id)
    )
    team_members = members_result.scalars().all()

    count = len(team_members)
    team_data = _team_to_response(team, count).model_dump()
    team_data["members"] = [
        {
            "user": UserResponse.model_validate(tm.user).model_dump(),
            "role": tm.role.value,
        }
        for tm in team_members
    ]

    return DataResponse(data=team_data)


# ---------- PATCH /orgs/{org_id}/teams/{team_id} ----------

@router.patch("/{team_id}")
async def update_team(
    org_id: str,
    team_id: str,
    body: TeamUpdate,
    member: OrgMember = Depends(get_org_member),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[TeamResponse]:
    team = await _get_team_or_404(db, org_id, team_id)
    await _require_admin_owner_or_lead(db, member, team_id)

    if body.name is not None:
        team.name = body.name
    if body.description is not None:
        team.description = body.description
    await db.flush()

    count = await _count_team_members(db, team_id)
    return DataResponse(data=_team_to_response(team, count))


# ---------- DELETE /orgs/{org_id}/teams/{team_id} ----------

@router.delete("/{team_id}", status_code=204)
async def delete_team(
    org_id: str,
    team_id: str,
    member: OrgMember = Depends(require_org_role(OrgRole.ADMIN, OrgRole.OWNER)),
    db: AsyncSession = Depends(get_db),
):
    team = await _get_team_or_404(db, org_id, team_id)
    await db.delete(team)
    await db.flush()
    return Response(status_code=204)


# ---------- POST /orgs/{org_id}/teams/{team_id}/members ----------

@router.post("/{team_id}/members", status_code=201)
async def add_team_member(
    org_id: str,
    team_id: str,
    body: TeamMemberAdd,
    member: OrgMember = Depends(get_org_member),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    await _get_team_or_404(db, org_id, team_id)
    await _require_admin_owner_or_lead(db, member, team_id)

    # Check user is org member
    org_member_result = await db.execute(
        select(OrgMember).where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == body.user_id,
        )
    )
    if not org_member_result.scalar_one_or_none():
        raise NotFoundException("org_member", body.user_id)

    # Check not already in team
    existing = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == body.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictException(
            code="ALREADY_TEAM_MEMBER",
            message="User is already a member of this team",
        )

    tm = TeamMember(team_id=team_id, user_id=body.user_id, role=body.role)
    db.add(tm)
    await db.flush()

    # Load user for response
    user_result = await db.execute(select(User).where(User.id == body.user_id))
    user = user_result.scalar_one()

    return DataResponse(
        data={
            "user": UserResponse.model_validate(user).model_dump(),
            "role": tm.role.value,
        }
    )


# ---------- DELETE /orgs/{org_id}/teams/{team_id}/members/{user_id} ----------

@router.delete("/{team_id}/members/{user_id}", status_code=204)
async def remove_team_member(
    org_id: str,
    team_id: str,
    user_id: str,
    member: OrgMember = Depends(get_org_member),
    db: AsyncSession = Depends(get_db),
):
    await _get_team_or_404(db, org_id, team_id)
    await _require_admin_owner_or_lead(db, member, team_id)

    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    )
    tm = result.scalar_one_or_none()
    if not tm:
        raise NotFoundException("team_member", user_id)

    await db.delete(tm)
    await db.flush()
    return Response(status_code=204)
