from datetime import datetime

from pydantic import BaseModel

from app.models.org import OrgRole

from .auth import UserResponse


class OrgCreate(BaseModel):
    name: str
    slug: str


class OrgUpdate(BaseModel):
    name: str | None = None
    avatar_url: str | None = None


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrgMemberResponse(BaseModel):
    id: str
    user: UserResponse
    role: OrgRole
    joined_at: datetime

    model_config = {"from_attributes": True}


class InviteMemberRequest(BaseModel):
    email: str
    role: OrgRole = OrgRole.MEMBER


class UpdateRoleRequest(BaseModel):
    role: OrgRole
