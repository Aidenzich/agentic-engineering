import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException, ConflictException
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.deps.auth import get_current_user
from app.events.bus import event_bus
from app.models.org import OrgMember, OrgRole, Organization, RefreshToken, User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import DataResponse

router = APIRouter(prefix="/api/v1", tags=["auth"])

REFRESH_TOKEN_MAX_AGE = 604800  # 7 days
REFRESH_TOKEN_PATH = "/api/v1/auth"


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _build_jwt_payload(user: User) -> dict:
    return {"sub": user.id, "email": user.email, "name": user.name}


async def _create_refresh_token(
    db: AsyncSession, user_id: str, request: Request
) -> str:
    """Create a refresh token, store hashed version in DB, return raw UUID."""
    raw_token = str(uuid.uuid4())
    token_hash = hash_password(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_MAX_AGE)

    rt = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(rt)
    await db.flush()
    return raw_token


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=raw_token,
        httponly=True,
        samesite="lax",
        path=REFRESH_TOKEN_PATH,
        max_age=REFRESH_TOKEN_MAX_AGE,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key="refresh_token",
        path=REFRESH_TOKEN_PATH,
    )


# ---------- POST /auth/register ----------

@router.post("/auth/register", status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AuthResponse]:
    # Check existing email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise ConflictException(
            code="EMAIL_EXISTS", message="A user with this email already exists"
        )

    # Create user
    user = User(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.flush()

    # Create default org
    slug = _slugify(body.name)
    # Ensure slug uniqueness by appending short id if needed
    slug_exists = await db.execute(
        select(Organization).where(Organization.slug == slug)
    )
    if slug_exists.scalar_one_or_none():
        slug = f"{slug}-{user.id[:8]}"

    org = Organization(name=f"{body.name}'s Org", slug=slug)
    db.add(org)
    await db.flush()

    membership = OrgMember(org_id=org.id, user_id=user.id, role=OrgRole.OWNER)
    db.add(membership)
    await db.flush()

    # Tokens
    access_token = create_access_token(_build_jwt_payload(user))
    raw_refresh = await _create_refresh_token(db, user.id, request)
    _set_refresh_cookie(response, raw_refresh)

    await event_bus.emit(
        "audit.user_registered",
        org_id=org.id,
        actor_id=user.id,
        action="user.registered",
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    return DataResponse(
        data=AuthResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )
    )


# ---------- POST /auth/login ----------

@router.post("/auth/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AuthResponse]:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise AppException(
            status_code=401, code="INVALID_CREDENTIALS", message="Invalid email or password"
        )

    access_token = create_access_token(_build_jwt_payload(user))
    raw_refresh = await _create_refresh_token(db, user.id, request)
    _set_refresh_cookie(response, raw_refresh)

    return DataResponse(
        data=AuthResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )
    )


# ---------- POST /auth/refresh ----------

@router.post("/auth/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> DataResponse[TokenResponse]:
    if not refresh_token:
        raise AppException(
            status_code=401, code="NO_REFRESH_TOKEN", message="Refresh token not provided"
        )

    # Find all non-revoked, non-expired tokens and verify hash
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
    )
    tokens = result.scalars().all()

    matched_token: RefreshToken | None = None
    for t in tokens:
        if verify_password(refresh_token, t.token_hash):
            matched_token = t
            break

    if not matched_token:
        raise AppException(
            status_code=401,
            code="INVALID_REFRESH_TOKEN",
            message="Invalid or expired refresh token",
        )

    # Revoke old token
    matched_token.revoked_at = now
    await db.flush()

    # Get user
    user_result = await db.execute(
        select(User).where(User.id == matched_token.user_id)
    )
    user = user_result.scalar_one()

    # Create new tokens
    access_token = create_access_token(_build_jwt_payload(user))
    raw_refresh = await _create_refresh_token(db, user.id, request)
    _set_refresh_cookie(response, raw_refresh)

    return DataResponse(data=TokenResponse(access_token=access_token))


# ---------- POST /auth/logout ----------

@router.post("/auth/logout", status_code=204)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    _clear_refresh_cookie(response)
    return Response(status_code=204)


# ---------- GET /users/me ----------

@router.get("/users/me")
async def get_me(
    current_user: User = Depends(get_current_user),
) -> DataResponse[UserResponse]:
    return DataResponse(data=UserResponse.model_validate(current_user))


# ---------- PATCH /users/me ----------

class _UpdateMeBody(BaseModel):
    name: str | None = None
    avatar_url: str | None = None


@router.patch("/users/me")
async def update_me(
    body: _UpdateMeBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[UserResponse]:
    if body.name is not None:
        current_user.name = body.name
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url
    await db.flush()
    return DataResponse(data=UserResponse.model_validate(current_user))
