import uuid
from datetime import datetime

from sqlalchemy import (
    UUID,
    DateTime,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

class App(Base):
    """
    应用模型
    """

    __tablename__ = "apps"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_apps_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        nullable=False,
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    sandbox_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)

    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)

    title: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("''::character varying")
    )

    unread_message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    latest_message: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("''::text")
    )

    latest_message_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("''::character varying")
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
