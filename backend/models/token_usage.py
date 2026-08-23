from datetime import datetime, timezone
import uuid
from sqlalchemy import String, UUID, ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conversations.id"), nullable=True, index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    chat_message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chat_messages.id"), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="llm")  # llm | embedding | summary
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
