import json
import uuid

from anyio import to_thread
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat_message import ChatMessage
from models.conversation import Conversation
from schemas.chat_message import ChatQuestion
from services import doc_retrieval
from api.v1.controllers.document import agent


async def chat_message_stream(data: ChatQuestion, user_id: uuid.UUID, db: AsyncSession):
    yield f"data: {json.dumps({'event': 'start'})}\n\n"
    conversation = await db.get(Conversation, uuid.UUID(data.conversation_id))
    if conversation is None:
        return

    context = await to_thread.run_sync(
        doc_retrieval.retrieve_the_doc,
        data.query.strip(),
        str(user_id),
        str(conversation.document_id),
    )
    user_prompt = f"Document context:\n{context}\n\nQuestion: {data.query.strip()}"

    full_answer = ""
    async with agent.run_stream(user_prompt) as result:
        async for chunk in result.stream_text():
            full_answer += chunk
            yield f"data: {json.dumps({'event': 'token', 'content': chunk})}\n\n"

    db.add(ChatMessage(
        document_id=conversation.document_id,
        conversation_id=uuid.UUID(data.conversation_id),
        role="assistant",
        content=full_answer,
    ))
    await db.commit()

    yield f"data: {json.dumps({'event': 'done'})}\n\n"
