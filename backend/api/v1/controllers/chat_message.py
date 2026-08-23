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
from services.token_usage_service import estimate_tokens, extract_usage_tokens, record_token_usage
from api.v1.controllers.document import agent


@retry_llm
async def _run_agent_stream(prompt: str) -> tuple[str, object | None]:
    """Run LLM streaming with retry on 429/timeout/5xx. Returns (text, usage)."""
    full = ""
    usage = None
    async with agent.run_stream(prompt) as result:
        async for chunk in result.stream_text():
            full += chunk
        try:
            usage = result.usage()
        except Exception:
            usage = getattr(result, "usage", None)
    return full, usage

MAX_HISTORY_MESSAGES = 5
MAX_MESSAGE_LENGTH = 4000

SUMMARY_QA_COUNT = 12
SUMMARY_WINDOW_MESSAGES = SUMMARY_QA_COUNT * 2
SUMMARY_MAX_CHARS = 12000

async def _fetch_ordered_messages(
    conversation_id: uuid.UUID,
    current_query: str,
    db: AsyncSession,
    limit: int,
) -> list[ChatMessage]:
    """Shared fetch: get newest `limit` messages, return oldest->newest, strip pending current_query."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = list(reversed(result.scalars().all()))
    if messages and messages[-1].role == "user" and messages[-1].content == current_query:
        messages.pop()
    return messages


async def _get_conversation_history(
    conversation_id: uuid.UUID,
    current_query: str,
    db: AsyncSession,
) -> list[ChatMessage]:
    messages = await _fetch_ordered_messages(
        conversation_id, current_query, db, MAX_HISTORY_MESSAGES + 1
    )
    return messages[-MAX_HISTORY_MESSAGES:]


def _format_conversation_history(messages: list[ChatMessage]) -> str:
    if not messages:
        return "(No previous messages)"

    return "\n".join(
        f"{message.role.title()}: {message.content[:MAX_MESSAGE_LENGTH]}"
        for message in messages
    )


@retry_llm
async def _summarize_history(formatted_history: str) -> tuple[str, object | None]:
    prompt = (
        f"Summarise the following conversation history concisely. "
        f"Preserve key facts, user intents, decisions, and assistant answers "
        f"needed to continue the conversation. The history contains up to "
        f"{SUMMARY_QA_COUNT} Q&A pairs (up to {SUMMARY_WINDOW_MESSAGES} messages). "
        f"Return a compact summary (no preamble, no invented details):\n\n"
        f"{formatted_history[:SUMMARY_MAX_CHARS]}"
    )
    result = await agent.run(prompt)
    output = getattr(result, "output", None)
    if output is None:
        output = getattr(result, "data", "")
    usage = None
    try:
        usage = result.usage() if callable(getattr(result, "usage", None)) else getattr(result, "usage", None)
    except Exception:
        usage = None
    return (str(output).strip() if output else ""), usage


async def _get_history_context(
    conversation_id: uuid.UUID,
    current_query: str,
    db: AsyncSession,
) -> str:

    messages = await _fetch_ordered_messages(
        conversation_id,
        current_query,
        db,
        MAX_HISTORY_MESSAGES + SUMMARY_WINDOW_MESSAGES + 1,
    )

    if not messages:
        return "(No previous messages)"

    if len(messages) <= MAX_HISTORY_MESSAGES:
        return _format_conversation_history(messages[-MAX_HISTORY_MESSAGES:])

    recent_messages = messages[-MAX_HISTORY_MESSAGES:]
    older_messages = messages[-(MAX_HISTORY_MESSAGES + SUMMARY_WINDOW_MESSAGES) : -MAX_HISTORY_MESSAGES]
    if not older_messages:
        older_messages = messages[:-MAX_HISTORY_MESSAGES]
        older_messages = older_messages[-SUMMARY_WINDOW_MESSAGES:]

    formatted_older = _format_conversation_history(older_messages)
    formatted_recent = _format_conversation_history(recent_messages)

    try:
        summary, _usage = await _summarize_history(formatted_older)
        if not summary:
            raise ValueError("Empty summary")
        # usage for summary will be recorded by caller if needed; store for downstream
        # We cannot log here without db/user context, so just return summary
        # Caller (chat_message_stream) will handle logging if _usage is not None
        # To avoid losing usage, we attach it via closure attribute
        _get_history_context.last_summary_usage = _usage  # type: ignore
    except Exception:
        _get_history_context.last_summary_usage = None  # type: ignore
        return (
            f"Earlier conversation (truncated, summarisation unavailable):\n"
            f"{formatted_older}\n\n"
            f"Recent conversation (last {MAX_HISTORY_MESSAGES} messages):\n"
            f"{formatted_recent}"
        )

    return (
        f"Summary of earlier conversation (last {len(older_messages)} messages / up to {SUMMARY_QA_COUNT} Q&A):\n"
        f"{summary}\n\n"
        f"Recent conversation (last {MAX_HISTORY_MESSAGES} messages, verbatim):\n"
        f"{formatted_recent}"
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

    # helper to safely record usage without breaking stream
    async def _safe_record(**kwargs):
        try:
            await record_token_usage(db, user_id=user_id, conversation_id=conversation.id, document_id=conversation.document_id, **kwargs)
        except Exception:
            pass

    try:
        try:
            cached_answer, similarity = await to_thread.run_sync(
                semantic_cache.lookup,
                data.query.strip(),
                str(user_id),
                str(conversation.document_id),
            )
            if cached_answer:
                yield f"data: {json.dumps({'event': 'cached', 'similarity': similarity})}\n\n"
                for start in range(0, len(cached_answer), 400):
                    yield f"data: {json.dumps({'event': 'token', 'content': cached_answer[start:start + 400]})}\n\n"
                msg = ChatMessage(
                    document_id=conversation.document_id,
                    conversation_id=uuid.UUID(data.conversation_id),
                    role="assistant",
                    content=cached_answer,
                )
                db.add(msg)
                await db.flush()
                # cached hits still log 0 tokens but mark as cached for analytics
                await _safe_record(model="cache", source="llm", prompt_tokens=0, completion_tokens=0, chat_message_id=msg.id)
                await db.commit()
                yield f"data: {json.dumps({'event': 'done', 'cached': True})}\n\n"
                return
        except Exception:
            pass

        # --- embedding token logging (query embedding) ---
        try:
            # estimate tokens for query embedding before retrieval
            emb_tokens = estimate_tokens(data.query.strip())
            await _safe_record(model="all-MiniLM-L6-v2", source="embedding", prompt_tokens=emb_tokens, completion_tokens=0)
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
            history_context = await _get_history_context(
                uuid.UUID(data.conversation_id),
                data.query.strip(),
                db,
            )
            # log summary tokens if summarization happened
            try:
                summary_usage = getattr(_get_history_context, "last_summary_usage", None)
                if summary_usage is not None:
                    pt, ct = extract_usage_tokens(summary_usage)
                    if pt == 0 and ct == 0:
                        # fallback estimate
                        pt = estimate_tokens(history_context)
                        ct = estimate_tokens(summary_usage) if isinstance(summary_usage, str) else 50
                    await _safe_record(model="gpt-4o-mini", source="summary", prompt_tokens=pt, completion_tokens=ct)
            except Exception:
                pass
        except Exception:
            try:
                fallback = await _get_conversation_history(
                    uuid.UUID(data.conversation_id),
                    data.query.strip(),
                    db,
                )
                history_context = _format_conversation_history(fallback)
            except Exception:
                history_context = "(No previous messages)"
        user_prompt = (
            f"Document context:\n{context}\n\n"
            f"Conversation history:\n{history_context}\n\n"
            f"Current question:\n{data.query.strip()}"
        )

        full_answer = ""
        llm_usage = None
        try:
            full_answer, llm_usage = await _run_agent_stream(user_prompt)
            # log LLM usage
            try:
                pt, ct = extract_usage_tokens(llm_usage)
                if pt == 0 and ct == 0:
                    pt = estimate_tokens(user_prompt)
                    ct = estimate_tokens(full_answer)
                await _safe_record(model="gpt-4o-mini", source="llm", prompt_tokens=pt, completion_tokens=ct)
            except Exception:
                pass
        except Exception:
            raise

        safe_answer = mask_pii(full_answer)
        if not is_answer_grounded(safe_answer, context):
            yield f"data: {json.dumps({'event': 'error', 'content': 'The answer did not stay grounded in this document.'})}\n\n"
            return

        for start in range(0, len(safe_answer), 400):
            yield f"data: {json.dumps({'event': 'token', 'content': safe_answer[start:start + 400]})}\n\n"
        full_answer = safe_answer
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
