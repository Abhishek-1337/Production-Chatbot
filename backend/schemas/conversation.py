from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    title: str
    document_id: str
    document_name: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] | None = Field(default=None)
    total_messages: int | None = Field(default=None)


class ConversationListItem(BaseModel):
    id: str
    title: str
    document_id: str
    document_name: str | None = None
    updated_at: datetime


class PaginatedMessagesResponse(BaseModel):
    messages: list[MessageResponse]
    next_cursor: str | None = Field(default=None, description="ISO datetime cursor for next page")
    has_more: bool = False
    total: int | None = Field(default=None)
