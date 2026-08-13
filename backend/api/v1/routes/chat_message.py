import uuid
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from database import get_db
from models.chat_message import ChatMessage
from models.document import Document
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
    if not data.document_id:
        raise HTTPException(
            status_code=401,
            detail="Document id is not available."
        )
    result = await db.execute(select(Document).where(
        Document.id == data.document_id,
        Document.user_id == _current_user.id,
    ))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document not found."
        )

    db.add(ChatMessage(
        document_id=uuid.UUID(data.document_id),
        user_id=_current_user.id,
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