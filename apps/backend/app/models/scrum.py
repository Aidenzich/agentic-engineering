import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, new_id, utcnow


class WorkItemType(str, enum.Enum):
    EPIC = "epic"
    STORY = "story"
    TASK = "task"
    BUG = "bug"
    SPIKE = "spike"


class WorkItemStatus(str, enum.Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    QA = "qa"
    DONE = "done"
    CANCELLED = "cancelled"


class Priority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SprintStatus(str, enum.Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"


class PRStatus(str, enum.Enum):
    OPEN = "open"
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    MERGED = "merged"
    CLOSED = "closed"


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="projects")
    work_items: Mapped[list["WorkItem"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    sprints: Mapped[list["Sprint"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    __table_args__ = (
        UniqueConstraint("org_id", "slug"),
        UniqueConstraint("org_id", "prefix"),
    )


class TeamProject(Base):
    __tablename__ = "team_projects"
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)

    team: Mapped["Team"] = relationship(back_populates="projects")


class WorkItem(Base):
    __tablename__ = "work_items"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("work_items.id"))
    type: Mapped[WorkItemType] = mapped_column(SAEnum(WorkItemType), default=WorkItemType.STORY)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[WorkItemStatus] = mapped_column(SAEnum(WorkItemStatus), default=WorkItemStatus.BACKLOG)
    priority: Mapped[Priority] = mapped_column(SAEnum(Priority), default=Priority.MEDIUM)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    story_points: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, default=0)
    labels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    custom_fields: Mapped[dict | None] = mapped_column(JSONB)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship(back_populates="work_items")
    parent: Mapped["WorkItem | None"] = relationship(remote_side="WorkItem.id", back_populates="children")
    children: Mapped[list["WorkItem"]] = relationship(back_populates="parent")
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assignee_id])
    sprint_links: Mapped[list["SprintWorkItem"]] = relationship(
        back_populates="work_item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("project_id", "number"),
        Index("ix_work_items_project_status", "project_id", "status"),
        Index("ix_work_items_project_type", "project_id", "type"),
        Index("ix_work_items_project_parent", "project_id", "parent_id"),
    )


class Sprint(Base):
    __tablename__ = "sprints"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    goal: Mapped[str | None] = mapped_column(String)
    status: Mapped[SprintStatus] = mapped_column(SAEnum(SprintStatus), default=SprintStatus.PLANNING)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship(back_populates="sprints")
    work_items: Mapped[list["SprintWorkItem"]] = relationship(
        back_populates="sprint", cascade="all, delete-orphan"
    )
    __table_args__ = (Index("ix_sprints_project_status", "project_id", "status"),)


class SprintWorkItem(Base):
    __tablename__ = "sprint_work_items"
    sprint_id: Mapped[str] = mapped_column(ForeignKey("sprints.id", ondelete="CASCADE"), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sprint: Mapped["Sprint"] = relationship(back_populates="work_items")
    work_item: Mapped["WorkItem"] = relationship(back_populates="sprint_links")


class PullRequest(Base):
    __tablename__ = "pull_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    provider_type: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    repo_full_name: Mapped[str] = mapped_column(String, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str | None] = mapped_column(String)
    status: Mapped[PRStatus] = mapped_column(SAEnum(PRStatus), default=PRStatus.OPEN)
    author_login: Mapped[str] = mapped_column(String, nullable=False)
    head_branch: Mapped[str] = mapped_column(String, nullable=False)
    base_branch: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ci_status: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="pull_requests")
    comments: Mapped[list["PRComment"]] = relationship(back_populates="pr", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("org_id", "provider_type", "external_id"),
        Index("ix_pull_requests_org_status", "org_id", "status"),
    )


class PRComment(Base):
    __tablename__ = "pr_comments"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    pr_id: Mapped[str] = mapped_column(ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    author_login: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str | None] = mapped_column(String)
    line: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    pr: Mapped["PullRequest"] = relationship(back_populates="comments")
    __table_args__ = (UniqueConstraint("pr_id", "external_id"),)


from .org import Organization, Team, User  # noqa: E402, F401
