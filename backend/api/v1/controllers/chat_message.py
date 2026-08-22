import json
import logging
import traceback
import uuid

from anyio import to_thread
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat_message import ChatMessage
from models.conversation import Conversation
from schemas.chat_message import ChatQuestion
from services import doc_retrieval
from services.input_guardrails import (
    is_answer_grounded,
    mask_pii,
)
from api.v1.controllers.document import agent

logger = logging.getLogger(__name__)

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
        logger.info(
            "chat query user_id=%s conv=%s doc=%s q=%.120s",
            user_id,
            data.conversation_id,
            conversation.document_id,
            data.query.strip(),
        )
        try:
            context = await to_thread.run_sync(
                doc_retrieval.retrieve_the_doc,
                data.query.strip(),
                str(user_id),
                str(conversation.document_id),
            )
            logger.info("retrieved context chars=%d empty=%s", len(context), not bool(context.strip()))
        except Exception as ret_exc:
            logger.exception("retrieve_the_doc crashed, using empty context: %s", ret_exc)
            context = ""

        try:
            history = await _get_conversation_history(
                uuid.UUID(data.conversation_id),
                data.query.strip(),
                db,
            )
        except Exception as hist_exc:
            logger.exception("history fetch failed: %s", hist_exc)
            history = []
        user_prompt = (
            f"Document context:\n{context}\n\n"
            f"Conversation history:\n{_format_conversation_history(history)}\n\n"
            f"Current question:\n{data.query.strip()}"
        )

        full_answer = ""
        try:
            async with agent.run_stream(user_prompt) as result:
                async for chunk in result.stream_text():
                    full_answer += chunk
            logger.info("agent returned chars=%d", len(full_answer))
        except Exception as agent_exc:
            logger.exception("agent.run_stream failed: %s", agent_exc)
            raise

        safe_answer = mask_pii(full_answer)
        if not is_answer_grounded(safe_answer, context):
            logger.warning("answer not grounded, blocking: %.200s", safe_answer)
            yield f"data: {json.dumps({'event': 'error', 'content': 'The answer did not stay grounded in this document.'})}\n\n"
            return

        for start in range(0, len(safe_answer), 400):
            yield f"data: {json.dumps({'event': 'token', 'content': safe_answer[start:start + 400]})}\n\n"
        full_answer = safe_answer
    except Exception as error:
        logger.exception("chat_message_stream failed: %s\n%s", error, traceback.format_exc())
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
        except Exception as db_exc:
            logger.exception("failed to persist error message: %s", db_exc)
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
