#!/usr/bin/env python3
"""
One-time repair for semantic_cache dimension mismatch.

Prints inventory before/after deleting the semantic_cache collection.
Does NOT touch the `documents` collection.

Usage:
  python backend/scripts/fix_semantic_cache_dim.py
  # or from backend/:
  python scripts/fix_semantic_cache_dim.py
"""
from pathlib import Path
import sys

# Ensure backend root is importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import chromadb

CHROMA_PATH = str(BACKEND_DIR / "chroma_db")


def inventory(client: chromadb.PersistentClient):
    cols = client.list_collections()
    if not cols:
        print("  (no collections)")
        return
    for c in cols:
        name = c.name
        try:
            cnt = c.count()
        except Exception as e:
            cnt = f"error: {e}"
        try:
            md = c.metadata
        except Exception:
            md = None
        print(f"  - {name}: count={cnt} metadata={md}")


def main():
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    print(f"Chroma path: {CHROMA_PATH}")
    print("\n=== BEFORE ===")
    inventory(client)

    # Record documents count before
    try:
        docs_col = client.get_collection("documents")
        docs_before = docs_col.count()
        docs_meta_before = docs_col.metadata
    except Exception:
        docs_before = None
        docs_meta_before = None
        print("  documents collection not found (will be None)")

    # Delete semantic_cache if exists
    exists = any(c.name == "semantic_cache" for c in client.list_collections())
    if exists:
        print("\nDeleting collection `semantic_cache`...")
        client.delete_collection("semantic_cache")
        print("Deleted `semantic_cache`.")
    else:
        print("\n`semantic_cache` does not exist — nothing to delete.")

    print("\n=== AFTER ===")
    inventory(client)

    # Verify documents unchanged
    try:
        docs_col_after = client.get_collection("documents")
        docs_after = docs_col_after.count()
        docs_meta_after = docs_col_after.metadata
        print(f"\nDocuments count before={docs_before} after={docs_after} unchanged={docs_before==docs_after}")
        print(f"Documents metadata before={docs_meta_before} after={docs_meta_after}")
        if docs_before is not None and docs_before != docs_after:
            print("ERROR: documents count changed!", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        if docs_before is None:
            print(f"documents still not found after (expected if it never existed): {e}")
        else:
            print(f"ERROR: documents collection missing after delete: {e}", file=sys.stderr)
            sys.exit(1)

    # Verify semantic_cache gone
    still_exists = any(c.name == "semantic_cache" for c in client.list_collections())
    if still_exists:
        print("ERROR: semantic_cache still exists after delete!", file=sys.stderr)
        sys.exit(1)
    else:
        print("Verified `semantic_cache` is gone (will be recreated with correct dim on next write).")

    print("\nDone. `documents` untouched, `semantic_cache` cleared.")


if __name__ == "__main__":
    main()
