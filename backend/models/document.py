from typing import TYPE_CHECKING
from sqlalchemy import String, UUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
import uuid
# from models.user import User
if TYPE_CHECKING:
    from models.chat_message import ChatMessage


if TYPE_CHECKING:
    from models.user import User
    from models.conversation import Conversation

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default = uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id")
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user: Mapped["User"] = relationship(
        "User",
        back_populates = "documents"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="document"
    )
