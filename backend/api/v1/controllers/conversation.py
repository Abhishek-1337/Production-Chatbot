from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import Conversation
from models.document import Document
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


async def get_user_conversations(user: User, db: AsyncSession) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .options(selectinload(Conversation.document))
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_user_conversation(conversation_id: str, user: User, db: AsyncSession) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        ).options(selectinload(Conversation.document), selectinload(Conversation.messages))
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
