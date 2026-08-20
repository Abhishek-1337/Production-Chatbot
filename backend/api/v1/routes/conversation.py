from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.conversation import ConversationListItem, ConversationResponse
from services.auth import get_current_user
from api.v1.controllers.conversation import (
    create_conversation_from_upload,
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


def as_response(conversation):
    return {
        **as_list_item(conversation),
        "created_at": conversation.created_at,
        "messages": [
            {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in conversation.messages
        ],
    }


@router.get("", response_model=list[ConversationListItem])
async def list_conversations(
    user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]
):
    conversations = await get_user_conversations(user, db)
    return [as_list_item(conversation) for conversation in conversations]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]
):
    conversation = await get_user_conversation(conversation_id, user, db)
    return as_response(conversation)


@router.post("/upload", response_model=ConversationResponse, status_code=201)
async def upload_conversation(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    conversation = await create_conversation_from_upload(file, user, db)
    conversation = await get_user_conversation(str(conversation.id), user, db)
    return as_response(conversation)
