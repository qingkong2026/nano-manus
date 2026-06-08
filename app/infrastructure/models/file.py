import uuid
from datetime import datetime

from sqlalchemy import (
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


class File(Base):
    """
    应用文件模型
    """

    __tablename__ = "files"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_files_id"),
        Index("idx_files_app_id", "app_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        nullable=False,
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    app_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)

    filename: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("''::character varying")
    )

    filepath: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("''::character varying")
    )

    key: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("''::character varying")
    )

    extension: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("''::character varying")
    )

    mime_type: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("''::character varying")
    )

    size: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

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
