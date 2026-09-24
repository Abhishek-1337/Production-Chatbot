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


# USD per 1M tokens: (input_rate, output_rate).
# - gpt-4o-mini serves chat + summary rows (the only billable model in use).
# - all-MiniLM-L6-v2 runs locally via sentence-transformers: $0.
# - "cache" rows log 0 tokens: $0.
# - Unknown models default to $0 (never invent charges for a label we
#   don't recognize). Update these rates when OpenAI reprices.
MODEL_PRICING_USD_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "text-embedding-3-small": (0.02, 0.02),
    "all-minilm-l6-v2": (0.0, 0.0),
    "cache": (0.0, 0.0),
}


def cost_usd_for(
    model: str | None,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Cost in USD for a token count under a model label. Unknown models cost $0."""
    rates = MODEL_PRICING_USD_PER_1M.get((model or "").strip().lower(), (0.0, 0.0))
    return (prompt_tokens * rates[0] + completion_tokens * rates[1]) / 1_000_000


def total_cost_usd(rows) -> float:
    """Sum cost over aggregated rows carrying model/prompt_tokens/completion_tokens."""
    total = 0.0
    for r in rows:
        prompt = int(getattr(r, "prompt_tokens", 0) or 0)
        completion = int(getattr(r, "completion_tokens", 0) or 0)
        total += cost_usd_for(getattr(r, "model", None), prompt, completion)
    return total


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
