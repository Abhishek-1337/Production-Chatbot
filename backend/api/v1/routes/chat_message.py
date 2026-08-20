import uuid
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from database import get_db
from models.chat_message import ChatMessage
from models.conversation import Conversation
from models.user import User
from schemas.chat_message import ChatQuestion
from services.auth import get_current_user
from api.v1.controllers.chat_message import chat_message_stream

router = APIRouter(
    prefix="/chat",
    tags=["chats"]
)

@router.post("/")
async def chat_with_doc(
    data: ChatQuestion,
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if not data.conversation_id:
        raise HTTPException(
            status_code=401,
            detail="Conversation id is not available."
        )
    result = await db.execute(select(Conversation).where(
        Conversation.id == data.conversation_id,
        Conversation.user_id == _current_user.id,
    ))
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document not found."
        )

    db.add(ChatMessage(
        document_id=conversation.document_id,
        conversation_id=uuid.UUID(data.conversation_id),
        role="user",
        content=data.query.strip(),
    ))
    await db.commit()

    return StreamingResponse(
        chat_message_stream(data, _current_user.id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
