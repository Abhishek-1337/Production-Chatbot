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
    user: Mapped["User"] = relationship(
        "User",
        back_populates = "documents"
    )

