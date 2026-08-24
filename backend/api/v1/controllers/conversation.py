import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat_message import ChatMessage
from models.conversation import Conversation
from models.document import Document
from models.token_usage import TokenUsage
from models.user import User
from services import ingest, parser


ALLOWED_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


async def create_conversation_from_upload(
    file: UploadFile, user: User, db: AsyncSession
) -> Conversation:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="File type is not allowed")
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file name is required")

    document = Document(user_id=user.id, name=file.filename)
    db.add(document)
    await db.flush()

    conversation = Conversation(
        user_id=user.id,
        document_id=document.id,
        title=file.filename.rsplit(".", 1)[0][:255],
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    text = parser.parser(file)
    ingest.ingest_doc(text, document.id, str(user.id))
    return conversation


async def get_user_conversations(
    user: User, db: AsyncSession, limit: int = 20, offset: int = 0
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .options(selectinload(Conversation.document))
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    conversations = list(result.scalars().all())
    return conversations


async def get_user_conversation(conversation_id: str, user: User, db: AsyncSession) -> Conversation:
    """
    Returns conversation metadata only (without messages).
    Use get_conversation_messages for paginated message fetch.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_uuid, Conversation.user_id == user.id
        ).options(selectinload(Conversation.document))
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


async def delete_conversation(
    conversation_id: str, user: User, db: AsyncSession
) -> None:
    """
    Deletes the conversation and cascades to its chat messages.
    Ownership enforced by user_id filter.
    Also cleans up token_usage, document, chroma vectors and semantic cache
    that would otherwise block the DELETE via FK constraints.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_uuid, Conversation.user_id == user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    document_id = conversation.document_id


    await db.execute(delete(TokenUsage).where(TokenUsage.conversation_id == conv_uuid))
    subq = select(ChatMessage.id).where(ChatMessage.conversation_id == conv_uuid)
    await db.execute(delete(TokenUsage).where(TokenUsage.chat_message_id.in_(subq)))
    await db.flush()


    await db.execute(delete(ChatMessage).where(ChatMessage.conversation_id == conv_uuid))
    await db.flush()

    await db.delete(conversation)
    await db.flush()

    remaining = await db.execute(
        select(func.count()).select_from(Conversation).where(Conversation.document_id == document_id)
    )
    if remaining.scalar_one() == 0:
  
        await db.execute(delete(TokenUsage).where(TokenUsage.document_id == document_id))
        doc_result = await db.execute(select(Document).where(Document.id == document_id))
        doc = doc_result.scalar_one_or_none()
        if doc is not None:
            await db.delete(doc)
            await db.flush()

        try:
            from pathlib import Path
            import chromadb

            chroma_path = str(Path(__file__).resolve().parents[3] / "chroma_db")
            client = chromadb.PersistentClient(path=chroma_path)
            try:
                col = client.get_collection("documents")
                data = col.get(where={"document_id": str(document_id)}, include=[])
                ids = data.get("ids") or []
                if ids:
                    col.delete(ids=ids)
            except Exception:
                pass
            try:
                from services.semantic_cache import clear_scope

                clear_scope(user_id=str(user.id), document_id=str(document_id))
            except Exception:
                pass
        except Exception:
            pass

    await db.commit()


async def get_conversation_messages(
    conversation_id: str,
    user: User,
    db: AsyncSession,
    limit: int = 50,
    before: datetime | None = None,
) -> tuple[list[ChatMessage], bool, int]:
    """
    Keyset pagination for messages: WHERE created_at < before ORDER BY created_at DESC LIMIT.
    Returns (messages_asc, has_more, total_count). Messages are returned ASC for UI.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Verify ownership (metadata only) - cheap PK lookup
    ownership = await db.execute(
        select(Conversation.id).where(
            Conversation.id == conv_uuid, Conversation.user_id == user.id
        )
    )
    if ownership.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Count total for pagination UI
    total_result = await db.execute(
        select(func.count()).select_from(ChatMessage).where(ChatMessage.conversation_id == conv_uuid)
    )
    total = total_result.scalar_one()

    # Build keyset query: newest first, then reverse for ASC response
    query = select(ChatMessage).where(ChatMessage.conversation_id == conv_uuid)

    if before is not None:
        # Ensure timezone-aware
        if before.tzinfo is None:
            before = before.replace(tzinfo=timezone.utc)
        query = query.where(ChatMessage.created_at < before)

    query = query.order_by(ChatMessage.created_at.desc()).limit(limit + 1)

    result = await db.execute(query)
    rows = list(result.scalars().all())

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    # Return ASC for chat UI (oldest first)
    messages = list(reversed(rows))

    return messages, has_more, total
