from datetime import datetime

from pydantic import BaseModel

from app.models.org import TeamRole


class TeamCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class TeamResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    created_at: datetime
    member_count: int = 0

    model_config = {"from_attributes": True}


class TeamMemberAdd(BaseModel):
    user_id: str
    role: TeamRole = TeamRole.MEMBER
