"""
Semantic cache using OpenAI text embeddings + Chroma.

Stores (query -> answer) per (user_id, document_id). On lookup, embeds the
incoming query via OpenAI, does cosine nearest-neighbour search in Chroma and
returns the cached answer if cosine similarity >= threshold (default 0.93, env
SEMANTIC_CACHE_THRESHOLD, recommended 0.92-0.95).
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

import chromadb
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_CHROMA_PATH = str(_BACKEND_DIR / "chroma_db")
_COLLECTION_NAME = "semantic_cache"

_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.93"))
_EMBEDDING_MODEL = os.getenv("SEMANTIC_CACHE_EMBEDDING_MODEL", "text-embedding-3-small")
_ENABLED = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() not in ("0", "false", "no")

# Self-describing collection — update both when switching model (e.g. large = 3072)
EMBEDDING_MODEL = _EMBEDDING_MODEL
EMBEDDING_DIM = 1536 if "small" in _EMBEDDING_MODEL else 3072 if "large" in _EMBEDDING_MODEL else 1536
# Allow explicit dim override
if os.getenv("SEMANTIC_CACHE_EMBEDDING_DIM"):
    try:
        EMBEDDING_DIM = int(os.getenv("SEMANTIC_CACHE_EMBEDDING_DIM"))
    except Exception:
        pass

_cached_openai_client = None
_cached_chroma_client: chromadb.PersistentClient | None = None


def _get_chroma_client() -> chromadb.PersistentClient:
    global _cached_chroma_client
    if _cached_chroma_client is None:
        _cached_chroma_client = chromadb.PersistentClient(path=_CHROMA_PATH)
    return _cached_chroma_client


def _recreate_collection(client: chromadb.PersistentClient):
    """Delete and recreate semantic_cache with correct metadata. Returns new collection."""
    try:
        client.delete_collection(_COLLECTION_NAME)
    except Exception:
        pass
    return client.create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine", "embedding_model": EMBEDDING_MODEL, "embedding_dim": EMBEDDING_DIM},
    )


def get_semantic_cache_collection(client: chromadb.PersistentClient | None = None):
    """
    Self-describing helper: ensures collection metadata matches current EMBEDDING_MODEL/DIM.
    If mismatch or missing metadata, the stale collection is deleted and recreated.
    This intentionally drops old cached entries because embeddings from a different model/dim are incompatible.
    """
    if client is None:
        client = _get_chroma_client()
    try:
        col = client.get_collection(_COLLECTION_NAME)
        md = col.metadata or {}
        # Missing or mismatched metadata -> stale (e.g. legacy 3-D test data)
        if md.get("embedding_model") != EMBEDDING_MODEL or int(md.get("embedding_dim") or 0) != EMBEDDING_DIM:
            print(
                f"[SEMANTIC CACHE] metadata mismatch {md} vs model={EMBEDDING_MODEL} dim={EMBEDDING_DIM} -> recreating collection",
                flush=True,
            )
            logger.warning("semantic_cache metadata mismatch %s vs expected model=%s dim=%s -> recreating", md, EMBEDDING_MODEL, EMBEDDING_DIM)
            return _recreate_collection(client)
        return col
    except Exception as e:
        # get_collection raises if not found (e.g. ValueError / NotFoundError)
        # Treat as not-found -> create
        msg = str(e)
        if "does not exist" in msg.lower() or "not found" in msg.lower():
            return client.create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine", "embedding_model": EMBEDDING_MODEL, "embedding_dim": EMBEDDING_DIM},
            )
        # Unexpected error -> try recreate once
        print(f"[SEMANTIC CACHE] get_collection failed: {e} -> recreating", flush=True)
        logger.warning("semantic_cache get_collection failed: %s -> recreating", e)
        return _recreate_collection(client)


def _get_collection():
    """Backward compat — now delegates to self-describing helper."""
    return get_semantic_cache_collection()


def _get_openai_client():
    global _cached_openai_client
    if _cached_openai_client is not None:
        return _cached_openai_client
    try:
        import openai  # lazy import

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set — semantic cache disabled for embeddings")
            return None
        _cached_openai_client = openai.OpenAI(api_key=api_key)
        return _cached_openai_client
    except Exception as exc: 
        logger.exception("failed to init OpenAI client for semantic cache: %s", exc)
        return None


def _embed_query(text: str) -> Optional[list[float]]:
    """Embed `text` via OpenAI. Returns None on failure."""
    text = text.strip()
    if not text:
        return None
    client = _get_openai_client()
    if client is None:
        print("[SEMANTIC CACHE] OpenAI client not available", flush=True)
        return None
    try:
        resp = client.embeddings.create(model=_EMBEDDING_MODEL, input=text)
        print(f"[SEMANTIC CACHE] embedded q={text[:60]!r} model={_EMBEDDING_MODEL} dim={len(resp.data[0].embedding)}", flush=True)
        return resp.data[0].embedding  
    except Exception as exc:  
        print(f"[SEMANTIC CACHE] OpenAI embedding failed ({_EMBEDDING_MODEL}): {exc}", flush=True)
        logger.warning("OpenAI embedding failed (%s): %s", _EMBEDDING_MODEL, exc)
        return None


def is_enabled() -> bool:
    return _ENABLED


def get_threshold() -> float:
    return _THRESHOLD


def lookup(
    query: str,
    user_id: str,
    document_id: str,
    threshold: Optional[float] = None,
) -> Tuple[Optional[str], Optional[float]]:
    """
    Try to find a cached answer for `query` scoped to (user_id, document_id).

    Returns (cached_answer_or_None, similarity_or_None).
    similarity is cosine similarity in [ -1, 1 ], typically 0..1.
    """
    if not _ENABLED:
        print("[SEMANTIC CACHE] disabled, skipping lookup", flush=True)
        return None, None
    thr = threshold if threshold is not None else _THRESHOLD
    query = query.strip()
    if not query:
        return None, None

    print(f"[SEMANTIC CACHE] lookup q={query[:80]!r} user={user_id} doc={document_id} thr={thr}", flush=True)
    embedding = _embed_query(query)
    if embedding is None:
        print("[SEMANTIC CACHE] embedding failed, skipping cache", flush=True)
        return None, None

    try:
        collection = _get_collection()
        try:
            count = collection.count()
        except Exception:
            count = 1  
        if count == 0:
            return None, None

        where = {"$and": [{"user_id": user_id}, {"document_id": document_id}]}

        def _do_query(col):
            return col.query(
                query_embeddings=[embedding],
                n_results=1,
                where=where,
                include=["documents", "metadatas", "distances"],
            )

        try:
            results = _do_query(collection)
        except Exception as q_exc:
            if "expecting embedding with dimension" in str(q_exc).lower():
                print(f"[SEMANTIC CACHE] query dimension mismatch: {q_exc} -> recreating collection and retrying", flush=True)
                logger.warning("semantic_cache query dimension mismatch: %s -> recreating", q_exc)
                client = _get_chroma_client()
                try:
                    client.delete_collection(_COLLECTION_NAME)
                except Exception:
                    pass
                collection = get_semantic_cache_collection(client)
                results = _do_query(collection)
            else:
                raise
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        if not metadatas or not distances or metadatas[0] is None:
            return None, None

        distance = distances[0]
        try:
            distance_f = float(distance)
        except Exception:
            return None, None
        similarity = 1.0 - distance_f

        hit = similarity >= thr
        # Console visibility for cache debugging (backend terminal)
        print(
            f"[SEMANTIC CACHE] {'HIT' if hit else 'MISS'} | user={user_id} doc={document_id} "
            f"sim={similarity:.4f} thr={thr:.2f} q={query[:80]!r}",
            flush=True,
        )
        logger.info(
            "semantic_cache query user=%s doc=%s sim=%.4f thr=%.2f hit=%s",
            user_id,
            document_id,
            similarity,
            thr,
            hit,
        )

        if hit:
            answer = metadatas[0].get("answer")  # type: ignore[union-attr]
            if answer:
                print(f"[SEMANTIC CACHE] -> returning cached answer ({len(str(answer))} chars) sim={similarity:.4f}", flush=True)
                return str(answer), float(similarity)
            else:
                print("[SEMANTIC CACHE] hit but no answer in metadata", flush=True)
        else:
            print(f"[SEMANTIC CACHE] -> below threshold, will call LLM", flush=True)
        return None, float(similarity)
    except Exception as exc:  # pragma: no cover
        print(f"[SEMANTIC CACHE] lookup failed: {exc}", flush=True)
        logger.exception("semantic cache lookup failed: %s", exc)
        return None, None


def store(
    query: str,
    answer: str,
    user_id: str,
    document_id: str,
) -> bool:
    """
    Persist (query -> answer) for future semantic hits.
    Uses the same OpenAI embedding as lookup for consistency.
    Returns True on success.
    """
    if not _ENABLED:
        return False
    query = query.strip()
    answer = answer.strip()
    if not query or not answer:
        return False
    if answer.lower().startswith("i couldn't answer") or answer.lower().startswith("i cannot find"):
        return False

    embedding = _embed_query(query)
    if embedding is None:
        return False

    try:
        collection = _get_collection()
        MAX_META = 8000
        stored_answer = answer if len(answer) <= MAX_META else answer[:MAX_META]

        cache_id = str(uuid.uuid4())

        def _do_add(col, cid):
            col.add(
                ids=[cid],
                embeddings=[embedding],
                documents=[query],
                metadatas=[
                    {
                        "answer": stored_answer,
                        "user_id": user_id,
                        "document_id": document_id,
                    }
                ],
            )

        try:
            _do_add(collection, cache_id)
        except Exception as add_exc:
            if "expecting embedding with dimension" in str(add_exc).lower():
                print(f"[SEMANTIC CACHE] add dimension mismatch: {add_exc} -> recreating collection and retrying", flush=True)
                logger.warning("semantic_cache add dimension mismatch: %s -> recreating", add_exc)
                client = _get_chroma_client()
                try:
                    client.delete_collection(_COLLECTION_NAME)
                except Exception:
                    pass
                collection = get_semantic_cache_collection(client)
                _do_add(collection, cache_id)
            else:
                raise
        print(f"[SEMANTIC CACHE] STORE id={cache_id} user={user_id} doc={document_id} q={query[:60]!r} answer_len={len(stored_answer)}", flush=True)
        logger.info("semantic_cache store id=%s user=%s doc=%s q=%.60s", cache_id, user_id, document_id, query)
        return True
    except Exception as exc:  # pragma: no cover
        print(f"[SEMANTIC CACHE] store failed: {exc}", flush=True)
        logger.exception("semantic cache store failed: %s", exc)
        return False


def clear_scope(user_id: Optional[str] = None, document_id: Optional[str] = None) -> int:
    """Delete cached entries matching scope. Returns deleted count (best-effort)."""
    try:
        collection = _get_collection()
        where = None
        if user_id and document_id:
            where = {"$and": [{"user_id": user_id}, {"document_id": document_id}]}
        elif user_id:
            where = {"user_id": user_id}
        elif document_id:
            where = {"document_id": document_id}
        else:
            # dangerous: clear all — require explicit call
            pass

        if where is not None:
            # fetch ids to delete
            res = collection.get(where=where, include=[])  # type: ignore[arg-type]
            ids = res.get("ids") or []
            if ids:
                collection.delete(ids=ids)
                return len(ids)
            return 0
        return 0
    except Exception as exc:  # pragma: no cover
        logger.exception("semantic_cache clear failed: %s", exc)
        return 0
