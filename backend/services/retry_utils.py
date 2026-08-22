"""
Centralized retry policies using tenacity.

Operation -> Retry                                  | Don't retry
----------------------------------------------------|--------------------------------
LLM         429, timeout, 5xx                        | invalid request, auth
Embedding   429, timeout, 5xx                        | invalid input, auth
Vector DB query   timeout, connection error, 5xx      | malformed query
Vector DB insert  transient connection/5xx            | constraint/data errors
"""

from __future__ import annotations

import re
import asyncio

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_RETRYABLE_CODES = {429, *range(500, 600)}
_NON_RETRYABLE_CODES = {400, 401, 402, 403, 404, 405, 406, 407, 409, 410, 422}

_STATUS_RE = re.compile(r"\b(429|5\d{2}|400|401|403|404|422)\b")


def _get_status_code(exc: BaseException) -> int | None:
    for attr in ("status_code", "status", "code", "http_status", "http_code"):
        if hasattr(exc, attr):
            try:
                val = getattr(exc, attr)
                if isinstance(val, int):
                    return val
                if isinstance(val, str) and val.isdigit():
                    return int(val)
            except Exception:
                pass
    # inspect args / message for embedded code
    msg = str(exc)
    m = _STATUS_RE.search(msg)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    # OpenAI SDK stores response.status_code
    resp = getattr(exc, "response", None)
    if resp is not None:
        for attr in ("status_code", "status"):
            if hasattr(resp, attr):
                try:
                    val = getattr(resp, attr)
                    if isinstance(val, int):
                        return val
                except Exception:
                    pass
    return None


def _msg(exc: BaseException) -> str:
    try:
        return str(exc).lower()
    except Exception:
        return ""


def _is_timeout_or_connection(exc: BaseException) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError)):
        # OSError includes many connection errors, but filter by message
        msg = _msg(exc)
        if "timeout" in msg or "timed out" in msg or "connection" in msg or "temporarily unavailable" in msg:
            return True
        # bare TimeoutError / ConnectionError without message is retryable
        if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError)):
            return True
    msg = _msg(exc)
    if "timeout" in msg or "timed out" in msg:
        return True
    if "connection" in msg:
        return True
    if "api connection" in msg or "apiconnection" in msg:  # openai APIConnectionError
        return True
    return False


def _has_auth_keyword(msg: str) -> bool:
    return any(k in msg for k in ("authentication", "unauthorized", "unauthenticated", "api key", "apikey", "permission denied", "forbidden", "invalid api key"))

def _has_invalid_request_keyword(msg: str) -> bool:
    return any(k in msg for k in ("invalid request", "invalid_request", "bad request", "badrequest", "invalid input", "invalid_input", "unprocessable", "invalid argument"))

# ---------------------------------------------------------------------------
# predicates
# ---------------------------------------------------------------------------

def is_retryable_llm_exception(exc: BaseException) -> bool:
    """LLM: retry 429/timeout/5xx, do NOT retry invalid request / auth."""
    msg = _msg(exc)
    code = _get_status_code(exc)

    # Explicit non-retryable auth / invalid request
    if code in (400, 401, 403):
        return False
    if code == 404:  # model not found etc. -> invalid request
        return False
    if code == 422:
        return False
    if _has_auth_keyword(msg):
        # must check before generic 5xx retry to avoid mis-classify
        if "429" not in msg and code != 429:
            return False
    if _has_invalid_request_keyword(msg):
        # invalid request/input is never retryable even if message also contains 400 words
        # but allow retry if it's actually a 429/5xx
        if code not in _RETRYABLE_CODES:
            return False

    # Retryable checks
    if code == 429 or code in range(500, 600):
        return True
    # OpenAI typed errors (optional import)
    name = exc.__class__.__name__
    if name in ("RateLimitError", "InternalServerError", "APIConnectionError", "APITimeoutError", "APIError"):
        # APIError could be 400 or 500 - rely on code if available
        if code is not None:
            return code in _RETRYABLE_CODES
        # no code -> treat RateLimit/Internal/Timeout/Connection as retryable
        if name in ("RateLimitError", "InternalServerError", "APIConnectionError", "APITimeoutError"):
            return True
        return False
    if name in ("AuthenticationError", "PermissionDeniedError", "BadRequestError", "NotFoundError", "UnprocessableEntityError"):
        return False

    if _is_timeout_or_connection(exc):
        return True
    if "rate limit" in msg or "rate_limit" in msg:
        return True
    if "internal server" in msg or "server error" in msg:
        return True
    if "overloaded" in msg or "service unavailable" in msg or "bad gateway" in msg or "gateway timeout" in msg:
        return True
    return False


def is_retryable_embedding_exception(exc: BaseException) -> bool:
    """Embedding: same as LLM (429/timeout/5xx) but invalid input maps to 400."""
    # Embedding shares LLM logic; invalid input is treated as BadRequest
    return is_retryable_llm_exception(exc)


def is_retryable_vector_query_exception(exc: BaseException) -> bool:
    """Vector DB query: retry timeout/connection/5xx, don't retry malformed query."""
    msg = _msg(exc)
    code = _get_status_code(exc)
    name = exc.__class__.__name__

    # Malformed query -> InvalidArgument etc. -> never retry
    if name in ("InvalidArgumentError", "InvalidDimensionException", "InvalidUUIDError", "NotFoundError"):
        # NotFound for query is not retryable (collection missing is handled elsewhere)
        return False
    if "malformed" in msg or "invalid argument" in msg or "invalid dimension" in msg or "invalid uuid" in msg:
        return False
    if code == 400 or code == 422:
        return False

    # Retryable: timeout, connection, 5xx, rate limit, internal
    if code == 429 or (code is not None and 500 <= code <= 599):
        return True
    if name in ("InternalError", "RateLimitError"):
        return True
    if name in ("AuthorizationError", "ChromaAuthError"):
        return False
    if _is_timeout_or_connection(exc):
        return True
    if "internal" in msg and "error" in msg:
        return True
    return False


def is_retryable_vector_insert_exception(exc: BaseException) -> bool:
    """Vector DB insert: retry transient connection/5xx, don't retry constraint/data errors."""
    msg = _msg(exc)
    code = _get_status_code(exc)
    name = exc.__class__.__name__

    # Constraint / data errors -> never retry
    if name in ("DuplicateIDError", "IDAlreadyExistsError", "UniqueConstraintError", "BatchSizeExceededError", "InvalidArgumentError", "InvalidDimensionException", "InvalidUUIDError", "QuotaError"):
        return False
    if "duplicate" in msg or "already exists" in msg or "unique constraint" in msg or "batch size" in msg or "quota" in msg:
        return False
    if "invalid argument" in msg or "invalid dimension" in msg:
        return False
    if code in (400, 409, 422):  # 409 conflict = duplicate
        return False

    # Retryable: transient connection / 5xx / rate limit / internal
    if code == 429 or (code is not None and 500 <= code <= 599):
        return True
    if name in ("InternalError", "RateLimitError"):
        return True
    if _is_timeout_or_connection(exc):
        return True
    if "internal" in msg and "error" in msg:
        return True
    return False


# ---------------------------------------------------------------------------
# tenacity decorators
# ---------------------------------------------------------------------------

def _retry_decorator(predicate, *, attempts: int = 3, multiplier: float = 1, max_wait: float = 10):
    return retry(
        retry=retry_if_exception(predicate),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=multiplier, min=1, max=max_wait),
        reraise=True,
    )

# Exported decorators – use directly as @retry_llm etc.
retry_llm = _retry_decorator(is_retryable_llm_exception)
retry_embedding = _retry_decorator(is_retryable_embedding_exception)
retry_vector_query = _retry_decorator(is_retryable_vector_query_exception)
retry_vector_insert = _retry_decorator(is_retryable_vector_insert_exception)

# For async callers you can also use the same decorators (tenacity handles async).
# If you need custom attempts, use e.g. retry_llm_custom = _retry_decorator(..., attempts=5)
