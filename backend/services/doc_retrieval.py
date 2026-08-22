from pathlib import Path

import chromadb
from chonkie import SentenceTransformerEmbeddings

from services.retry_utils import retry_vector_query

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
            import os

            os.environ["HF_HUB_OFFLINE"] = "1"
            _cached_embeddings = SentenceTransformerEmbeddings(
                "sentence-transformers/all-MiniLM-L6-v2"
            )
    return _cached_embeddings


@retry_vector_query
def _query_documents(collection, query_embeddings, n_results, where):
    return collection.query(
        query_embeddings=query_embeddings,
        n_results=n_results,
        where=where,
    )


def retrieve_the_doc(query, user_id, document_id):
    try:
        collection = _get_client().get_or_create_collection(name="documents")
        embeddings = _get_embeddings()
        query_embedding = embeddings.embed(query)
        results = _query_documents(
            collection,
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
            return ""
        return "\n\n".join(docs)
    except Exception as exc:
        return ""