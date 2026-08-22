from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.conversation import ConversationListItem, ConversationResponse, PaginatedMessagesResponse
from services.auth import get_current_user
from api.v1.controllers.conversation import (
    create_conversation_from_upload,
    delete_conversation,
    get_conversation_messages,
    get_user_conversation,
    get_user_conversations,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def as_list_item(conversation):
    return {
        "id": str(conversation.id),
        "title": conversation.title,
        "document_id": str(conversation.document_id),
        "document_name": conversation.document.name if conversation.document else None,
        "updated_at": conversation.updated_at,
    }


def as_response(conversation, messages=None, total_messages=None):
    data = {
        **as_list_item(conversation),
        "created_at": conversation.created_at,
    }
    # Keep backwards compat: if caller fetched messages, include them
    if messages is not None:
        data["messages"] = [
            {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in messages
        ]
        data["total_messages"] = total_messages
    else:
        # Default for metadata-only: expose total_messages if available via lazy load fallback
        # Don't trigger lazy load; leave as None
        data["messages"] = None
        data["total_messages"] = total_messages
    return data


@router.get("", response_model=list[ConversationListItem])
async def list_conversations(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    conversations = await get_user_conversations(user, db, limit=limit, offset=offset)
    return [as_list_item(conversation) for conversation in conversations]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Metadata only — messages fetched via /{id}/messages
    conversation = await get_user_conversation(conversation_id, user, db)
    return as_response(conversation, messages=None, total_messages=None)


@router.get("/{conversation_id}/messages", response_model=PaginatedMessagesResponse)
async def list_conversation_messages(
    conversation_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100, description="Messages per page"),
    before: datetime | None = Query(None, description="ISO datetime cursor: fetch messages before this timestamp"),
):
    messages, has_more, total = await get_conversation_messages(
        conversation_id, user, db, limit=limit, before=before
    )
    # next_cursor is the oldest message's created_at for keyset pagination
    next_cursor = messages[0].created_at.isoformat() if has_more and messages else None
    return {
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in messages
        ],
        "next_cursor": next_cursor,
        "has_more": has_more,
        "total": total,
    }


@router.delete("/{conversation_id}", status_code=204)
async def remove_conversation(
    conversation_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await delete_conversation(conversation_id, user, db)
    return Response(status_code=204)


@router.post("/upload", response_model=ConversationResponse, status_code=201)
async def upload_conversation(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    conversation = await create_conversation_from_upload(file, user, db)
    conversation = await get_user_conversation(str(conversation.id), user, db)
    return as_response(conversation, messages=[], total_messages=0)
