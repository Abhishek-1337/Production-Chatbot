#!/usr/bin/env python3
"""
Remove poisoned semantic-cache entries holding self-repeating answers
(e.g. cumulative stream snapshots glued together by stream_text(delta=False)).

Scans the `semantic_cache` collection, deletes only entries whose stored
answer trips services.semantic_cache.is_degenerate_answer, and prints
inventory before/after. Does NOT touch the `documents` collection.

Usage:
  python backend/scripts/clear_poisoned_cache.py
  # or from backend/:
  python scripts/clear_poisoned_cache.py
"""
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import chromadb  

from services.semantic_cache import (  
    _CHROMA_PATH,
    _COLLECTION_NAME,
    is_degenerate_answer,
)


def main() -> int:
    client = chromadb.PersistentClient(path=_CHROMA_PATH)
    print(f"Chroma path: {_CHROMA_PATH}")

    try:
        collection = client.get_collection(_COLLECTION_NAME)
    except Exception:
        print(f"`{_COLLECTION_NAME}` does not exist — nothing to do.")
        return 0

    total = collection.count()
    print(f"`{_COLLECTION_NAME}` entries before: {total}")
    if total == 0:
        return 0

    res = collection.get(include=["documents", "metadatas"])
    ids = res.get("ids") or []
    docs = res.get("documents") or []
    metas = res.get("metadatas") or []

    poisoned_ids: list[str] = []
    for entry_id, query, meta in zip(ids, docs, metas):
        answer = (meta or {}).get("answer", "") or ""
        if is_degenerate_answer(answer):
            poisoned_ids.append(entry_id)
            print(f"  poisoned: query={(query or '')[:80]!r} answer_len={len(answer)}")

    if not poisoned_ids:
        print("No poisoned entries found — nothing to delete.")
        return 0

    collection.delete(ids=poisoned_ids)
    print(f"\nDeleted {len(poisoned_ids)} poisoned entries, "
          f"{collection.count()} remaining. `documents` untouched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
