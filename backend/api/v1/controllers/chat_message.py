import json
import uuid

from anyio import to_thread
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat_message import ChatMessage
from models.conversation import Conversation
from schemas.chat_message import ChatQuestion
from services import doc_retrieval
from api.v1.controllers.document import agent

MAX_HISTORY_MESSAGES = 12
MAX_MESSAGE_LENGTH = 4000


async def _get_conversation_history(
    conversation_id: uuid.UUID,
    current_query: str,
    db: AsyncSession,
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES + 1)
    )
    messages = list(reversed(result.scalars().all()))

    # The route persists the current user message before streaming starts.
    if messages and messages[-1].role == "user" and messages[-1].content == current_query:
        messages.pop()
    return messages[-MAX_HISTORY_MESSAGES:]


def _format_conversation_history(messages: list[ChatMessage]) -> str:
    if not messages:
        return "(No previous messages)"

    return "\n".join(
        f"{message.role.title()}: {message.content[:MAX_MESSAGE_LENGTH]}"
        for message in messages
    )


async def chat_message_stream(data: ChatQuestion, user_id: uuid.UUID, db: AsyncSession):
    yield f"data: {json.dumps({'event': 'start'})}\n\n"
    conversation = await db.get(Conversation, uuid.UUID(data.conversation_id))
    if conversation is None:
        return

    try:
        context = await to_thread.run_sync(
            doc_retrieval.retrieve_the_doc,
            data.query.strip(),
            str(user_id),
            str(conversation.document_id),
        )
        history = await _get_conversation_history(
            uuid.UUID(data.conversation_id),
            data.query.strip(),
            db,
        )
        user_prompt = (
            f"Document context:\n{context}\n\n"
            f"Conversation history:\n{_format_conversation_history(history)}\n\n"
            f"Current question:\n{data.query.strip()}"
        )

        full_answer = ""
        async with agent.run_stream(user_prompt) as result:
            async for chunk in result.stream_text():
                full_answer += chunk
                yield f"data: {json.dumps({'event': 'token', 'content': chunk})}\n\n"
    except Exception:
        yield f"data: {json.dumps({'event': 'error', 'content': 'I could not answer that question. Please try again.'})}\n\n"
        return

    db.add(ChatMessage(
        document_id=conversation.document_id,
        conversation_id=uuid.UUID(data.conversation_id),
        role="assistant",
        content=full_answer,
    ))
    await db.commit()

    yield f"data: {json.dumps({'event': 'done'})}\n\n"
