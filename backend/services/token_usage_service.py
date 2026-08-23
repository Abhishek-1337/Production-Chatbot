import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from models.token_usage import TokenUsage


def estimate_tokens(text: str) -> int:
    """Fallback token estimation (~4 chars per token). Tries tiktoken if available."""
    if not text:
        return 0
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4o-mini")
        return len(enc.encode(text))
    except Exception:
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return max(1, len(text) // 4)


async def record_token_usage(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    chat_message_id: uuid.UUID | None = None,
    model: str | None = None,
    source: str = "llm",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int | None = None,
) -> TokenUsage:
    if total_tokens is None:
        total_tokens = prompt_tokens + completion_tokens
    row = TokenUsage(
        user_id=user_id,
        conversation_id=conversation_id,
        document_id=document_id,
        chat_message_id=chat_message_id,
        model=model,
        source=source,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    db.add(row)
    # commit is handled by caller to avoid double commit; but flush so it persists with ChatMessage commit
    try:
        await db.flush()
    except Exception:
        pass
    return row


def extract_usage_tokens(usage_obj) -> tuple[int, int]:
    """Extract (prompt, completion) from pydantic-ai RunUsage or similar."""
    if usage_obj is None:
        return 0, 0
    try:
        prompt = getattr(usage_obj, "input_tokens", None)
        completion = getattr(usage_obj, "output_tokens", None)
        if prompt is not None and completion is not None:
            return int(prompt), int(completion)
        # fallback: request_tokens etc
        if hasattr(usage_obj, "prompt_tokens"):
            return int(usage_obj.prompt_tokens), int(getattr(usage_obj, "completion_tokens", 0))
        # dict-like
        if isinstance(usage_obj, dict):
            return int(usage_obj.get("prompt_tokens", usage_obj.get("input_tokens", 0))), int(usage_obj.get("completion_tokens", usage_obj.get("output_tokens", 0)))
    except Exception:
        pass
    return 0, 0
