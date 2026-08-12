from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, UUID, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
import uuid

if TYPE_CHECKING:
    from models.document import Document
    from models.chat_message import ChatMessage


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    password: Mapped[str] = mapped_column(
        String(255)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="user"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="user"
    )