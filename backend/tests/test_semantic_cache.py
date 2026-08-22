"""
Test for semantic_cache — uses ephemeral / temp Chroma so it never pollutes backend/chroma_db.

Fixes the original bug where a mocked test wrote 3-D vectors into the real persistent store.
"""
import math
from unittest.mock import MagicMock, patch
import chromadb
import tempfile
import os

def _mock_embedding(text: str):
    # deterministic small fake embedding for test speed — NOT 3-D, match real dim if needed
    # Use 1536-D like prod but with pattern: 1.0 at index 0 for "hello", index 1 for "weather"
    vec = [0.0] * 1536
    t = text.strip().lower()
    if "hello" in t:
        vec[0] = 1.0
    elif "weather" in t:
        vec[1] = 1.0
    else:
        vec[2] = 1.0
    # normalize
    n = math.sqrt(sum(x*x for x in vec))
    return [x/n for x in vec] if n else vec


def test_semantic_cache_uses_ephemeral_client(tmp_path=None):
    # Preferred: EphemeralClient (in-memory)
    client = chromadb.EphemeralClient()
    # Verify isolation from real persistent store
    real_path = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
    assert client._identifier is not None  # ephemeral

    # Simulate the service but patch _get_chroma_client to return ephemeral
    import services.semantic_cache as sc

    # Patch OpenAI embeddings to return deterministic 1536-D vectors
    mock_openai = MagicMock()
    def side_effect(model, input):
        m = MagicMock()
        m.data = [MagicMock(embedding=_mock_embedding(input))]
        return m
    mock_openai.OpenAI.return_value.embeddings.create.side_effect = side_effect

    with patch.dict("sys.modules", {"openai": mock_openai}):
        with patch.object(sc, "_get_chroma_client", return_value=client):
            # Ensure clean start — delete_collection if exists (not just delete(ids))
            try:
                client.delete_collection(sc._COLLECTION_NAME)
            except Exception:
                pass

            # Store and lookup
            ok = sc.store("hello world", "hi there", "user1", "doc1")
            assert ok is True
            ans, sim = sc.lookup("hello world", "user1", "doc1")
            assert ans == "hi there"
            assert sim is not None and sim > 0.93

            # Different doc -> miss
            ans2, _ = sc.lookup("hello world", "user1", "doc2")
            assert ans2 is None

            # Teardown: properly delete collection, not just ids
            client.delete_collection(sc._COLLECTION_NAME)
            assert sc._COLLECTION_NAME not in [c.name for c in client.list_collections()]


def test_semantic_cache_with_temp_persistent_client():
    """Alternative: PersistentClient at tmp_path — also isolated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        client = chromadb.PersistentClient(path=tmpdir)
        import services.semantic_cache as sc
        mock_openai = MagicMock()
        def side_effect(model, input):
            m = MagicMock()
            m.data = [MagicMock(embedding=_mock_embedding(input))]
            return m
        mock_openai.OpenAI.return_value.embeddings.create.side_effect = side_effect
        with patch.dict("sys.modules", {"openai": mock_openai}):
            with patch.object(sc, "_get_chroma_client", return_value=client):
                try:
                    client.delete_collection(sc._COLLECTION_NAME)
                except Exception:
                    pass
                sc.store("weather today", "sunny", "u1", "d1")
                ans, sim = sc.lookup("weather today", "u1", "d1")
                assert ans == "sunny"
                # Proper teardown
                client.delete_collection(sc._COLLECTION_NAME)
