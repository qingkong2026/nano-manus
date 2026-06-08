import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    UUID,
    DateTime,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Event(Base):
    """
    应用事件流模型
    """

    __tablename__ = "events"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_events_id"),
        Index("idx_events_app_id", "app_id"),
        Index("idx_events_position", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        nullable=False,
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    app_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)

    position: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    type: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("''::character varying")
    )

    data: Mapped[dict] = mapped_column(
        JSON, nullable=False, server_default=text("'{}'::json")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
        onupdate=datetime.now,
    )
