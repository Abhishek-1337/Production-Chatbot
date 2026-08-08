from sqlalchemy import String, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
import uuid 


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
    password: Mapped[String] = mapped_column(
        String(255)
    )
    documents:Mapped[list[str]] = relationship(
        back_populates="user"
    )