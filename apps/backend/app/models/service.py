import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, new_id, utcnow


class ServiceLifecycle(str, enum.Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


class Service(Base):
    __tablename__ = "services"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    lifecycle: Mapped[ServiceLifecycle] = mapped_column(
        SAEnum(ServiceLifecycle), default=ServiceLifecycle.DEVELOPMENT
    )
    tech_stack: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    owner_team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"))
    repo_url: Mapped[str | None] = mapped_column(String)
    metadata_: Mapped[dict | None] = mapped_column(JSONB, name="metadata")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="services")
    __table_args__ = (
        UniqueConstraint("org_id", "slug"),
        Index("ix_services_org_lifecycle", "org_id", "lifecycle"),
    )


class EntityLink(Base):
    __tablename__ = "entity_links"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String, nullable=False)
    link_type: Mapped[str] = mapped_column(String, nullable=False)
    source_page_id: Mapped[str | None] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"))
    source_work_item_id: Mapped[str | None] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"))
    source_pr_id: Mapped[str | None] = mapped_column(ForeignKey("pull_requests.id", ondelete="CASCADE"))
    source_service_id: Mapped[str | None] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"))
    target_page_id: Mapped[str | None] = mapped_column(ForeignKey("pages.id", ondelete="SET NULL"))
    target_work_item_id: Mapped[str | None] = mapped_column(ForeignKey("work_items.id", ondelete="SET NULL"))
    target_pr_id: Mapped[str | None] = mapped_column(ForeignKey("pull_requests.id", ondelete="SET NULL"))
    target_service_id: Mapped[str | None] = mapped_column(ForeignKey("services.id", ondelete="SET NULL"))
    target_external_url: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_entity_links_org_type", "org_id", "link_type"),
        Index("ix_entity_links_source_page", "source_page_id"),
        Index("ix_entity_links_source_item", "source_work_item_id"),
        Index("ix_entity_links_target_page", "target_page_id"),
        Index("ix_entity_links_target_item", "target_work_item_id"),
    )


from .org import Organization  # noqa: E402, F401
