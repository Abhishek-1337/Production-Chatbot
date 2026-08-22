import logging
from pathlib import Path

import chromadb
from chonkie import SentenceTransformerEmbeddings

logger = logging.getLogger(__name__)

_cached_client: chromadb.PersistentClient | None = None
_cached_embeddings: SentenceTransformerEmbeddings | None = None

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_CHROMA_PATH = str(_BACKEND_DIR / "chroma_db")


def _get_client() -> chromadb.PersistentClient:
    global _cached_client
    if _cached_client is None:
        _cached_client = chromadb.PersistentClient(path=_CHROMA_PATH)
    return _cached_client


def _get_embeddings() -> SentenceTransformerEmbeddings:
    global _cached_embeddings
    if _cached_embeddings is None:
        # local_files_only avoids HF hub round-trip after first cache
        try:
            _cached_embeddings = SentenceTransformerEmbeddings(
                "sentence-transformers/all-MiniLM-L6-v2"
            )
        except Exception as exc:
            logger.warning("Failed to load embeddings, retrying with local_files_only: %s", exc)
            # SentenceTransformer accepts trust_remote etc.; try with explicit local_files_only via underlying model kwargs
            # Fallback: force huggingface to use cache only
            import os

            os.environ["HF_HUB_OFFLINE"] = "1"
            _cached_embeddings = SentenceTransformerEmbeddings(
                "sentence-transformers/all-MiniLM-L6-v2"
            )
    return _cached_embeddings


def retrieve_the_doc(query, user_id, document_id):
    try:
        collection = _get_client().get_or_create_collection(name="documents")
        embeddings = _get_embeddings()
        query_embedding = embeddings.embed(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            where={
                "$and": [
                    {"user_id": user_id},
                    {"document_id": document_id},
                ]
            },
        )
        docs = (results.get("documents") or [[]])[0]
        if not docs:
            logger.warning(
                "retrieve_the_doc empty for user_id=%s document_id=%s query=%r",
                user_id,
                document_id,
                query[:80],
            )
            return ""
        return "\n\n".join(docs)
    except Exception as exc:
        logger.exception("retrieve_the_doc failed for %s/%s: %s", user_id, document_id, exc)
        # Fail open: return empty context so agent can still answer with fallback
        return ""