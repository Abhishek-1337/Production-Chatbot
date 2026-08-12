from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, UUID, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
import uuid

if TYPE_CHECKING:
    from models.user import User
    from models.document import Document


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id")
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="chat_messages"
    )
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="documents"
    )
    role: Mapped[str] = mapped_column(
        String(20)
    )
    content: Mapped[str] = mapped_column(
        Text
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )