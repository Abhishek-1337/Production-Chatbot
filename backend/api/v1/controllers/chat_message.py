import json
import uuid

from anyio import to_thread
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat_message import ChatMessage
from models.conversation import Conversation
from schemas.chat_message import ChatQuestion
from services import doc_retrieval, semantic_cache
from services.input_guardrails import (
    is_answer_grounded,
    mask_pii,
)
from services.retry_utils import retry_llm
from api.v1.controllers.document import agent


@retry_llm
async def _run_agent_stream(prompt: str) -> str:
    """Run LLM streaming with retry on 429/timeout/5xx. Retries transient failures."""
    full = ""
    async with agent.run_stream(prompt) as result:
        async for chunk in result.stream_text():
            full += chunk
    return full

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


async def chat_message_stream(
    data: ChatQuestion,
    user_id: uuid.UUID,
    db: AsyncSession,
):
    yield f"data: {json.dumps({'event': 'start'})}\n\n"
    conversation = await db.get(Conversation, uuid.UUID(data.conversation_id))

    if conversation is None:
        return

    try:
        # --- Semantic cache lookup (OpenAI embedding, threshold ~0.93) ---
        try:
            cached_answer, similarity = await to_thread.run_sync(
                semantic_cache.lookup,
                data.query.strip(),
                str(user_id),
                str(conversation.document_id),
            )
            if cached_answer:
                # stream cached answer in same chunked manner + mark as cached
                yield f"data: {json.dumps({'event': 'cached', 'similarity': similarity})}\n\n"
                for start in range(0, len(cached_answer), 400):
                    yield f"data: {json.dumps({'event': 'token', 'content': cached_answer[start:start + 400]})}\n\n"
                # persist cached hit as assistant message
                db.add(ChatMessage(
                    document_id=conversation.document_id,
                    conversation_id=uuid.UUID(data.conversation_id),
                    role="assistant",
                    content=cached_answer,
                ))
                await db.commit()
                yield f"data: {json.dumps({'event': 'done', 'cached': True})}\n\n"
                return
        except Exception:
            pass

        try:
            context = await to_thread.run_sync(
                doc_retrieval.retrieve_the_doc,
                data.query.strip(),
                str(user_id),
                str(conversation.document_id),
            )
        except Exception:
            context = ""

        try:
            history = await _get_conversation_history(
                uuid.UUID(data.conversation_id),
                data.query.strip(),
                db,
            )
        except Exception:
            history = []
        user_prompt = (
            f"Document context:\n{context}\n\n"
            f"Conversation history:\n{_format_conversation_history(history)}\n\n"
            f"Current question:\n{data.query.strip()}"
        )

        full_answer = ""
        try:
            full_answer = await _run_agent_stream(user_prompt)
        except Exception:
            raise

        safe_answer = mask_pii(full_answer)
        if not is_answer_grounded(safe_answer, context):
            yield f"data: {json.dumps({'event': 'error', 'content': 'The answer did not stay grounded in this document.'})}\n\n"
            return

        for start in range(0, len(safe_answer), 400):
            yield f"data: {json.dumps({'event': 'token', 'content': safe_answer[start:start + 400]})}\n\n"
        full_answer = safe_answer
        # store in semantic cache for future hits (best-effort, fail-open)
        try:
            await to_thread.run_sync(
                semantic_cache.store,
                data.query.strip(),
                safe_answer,
                str(user_id),
                str(conversation.document_id),
            )
        except Exception:
            pass
    except Exception:
        yield f"data: {json.dumps({'event': 'error', 'content': 'I could not answer that question. Please try again.'})}\n\n"
        full_answer = "I couldn't answer that question."
        try:
            await db.rollback()
            db.add(ChatMessage(
                document_id=conversation.document_id,
                conversation_id=uuid.UUID(data.conversation_id),
                role="assistant",
                content=full_answer,
            ))
            await db.commit()
        except Exception:
            try:
                await db.rollback()
            except Exception:
                pass
        return

    db.add(ChatMessage(
        document_id=conversation.document_id,
        conversation_id=uuid.UUID(data.conversation_id),
        role="assistant",
        content=full_answer,
    ))
    await db.commit()

    yield f"data: {json.dumps({'event': 'done'})}\n\n"
