#!/usr/bin/env python3
"""
Sprint 1 — SIDIX Brain Knowledge Inherit
==========================================
Day 73 | 2026-05-14 | M1.7 path to ADO organ architecture

Walks `/opt/sidix_kb/` (SIDIX brain/public mounted read-only inside the api
container) and ingests every markdown chunk into MiganCore's Qdrant collection
with a `bucket` payload field.

Bucket taxonomy (organ-inspired):
  ilm:coding         — 12 coding roadmap topics (ML, Python, DSA, etc)
  ilm:glossary       — technical + Islamic glossary
  ilm:curriculum     — structured learning paths
  ilm:faq            — frequently asked context
  ilm:domain         — omnyx_knowledge domain content
  patterns           — auto_learn + feedback_learning behavioral templates
  hikmah             — hafidz memorization wisdom + lessons
  maqashid           — purpose/intent frameworks
  aspirations        — (from /opt/sidix/brain/aspirations/induction.jsonl if mounted)

Idempotent: each chunk gets deterministic UUID from sha256(source_path + chunk_index),
so re-running upserts the same point (no duplicates).

Runs INSIDE the api container (has access to embedding service + Qdrant client):
    docker exec -i ado-api-1 python3 - < scripts/ingest_sidix_brain.py

Or after deploy:
    docker exec ado-api-1 python3 /app/scripts/ingest_sidix_brain.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, "/app")

# Core_brain agent_id (Mighan-Core in production DB)
CORE_BRAIN_ID = "cb3ebd3b-4c31-4af7-8470-25c2011c0974"
# Default tenant — for system-level inheritance ingest
SYSTEM_TENANT = "00000000-0000-0000-0000-000000000000"

KB_ROOT = Path("/opt/sidix_kb")
MAX_CHUNK_CHARS = 1200   # ~300-400 tokens, fits in 768-dim embedding context comfortably
CHUNK_OVERLAP = 150


# --------------------------------------------------------------------------
# Bucket detection from file path
# --------------------------------------------------------------------------
def detect_bucket(path: Path) -> str:
    parts = path.relative_to(KB_ROOT).parts
    if not parts:
        return "ilm:general"
    top = parts[0]
    return {
        "coding":            "ilm:coding",
        "glossary":          "ilm:glossary",
        "curriculum":        "ilm:curriculum",
        "faq":               "ilm:faq",
        "omnyx_knowledge":   "ilm:domain",
        "auto_learn":        "patterns",
        "feedback_learning": "patterns",
        "hafidz":            "hikmah",
        "maqashid":          "maqashid",
        "incoming":          "ilm:incoming",
    }.get(top, f"ilm:{top}")


# --------------------------------------------------------------------------
# Markdown chunking — paragraph-aware sliding window
# --------------------------------------------------------------------------
_HEADING_RE = re.compile(r"^#+\s", re.MULTILINE)


def chunk_markdown(text: str) -> list[str]:
    """Split markdown into ~MAX_CHUNK_CHARS chunks, prefer paragraph + heading boundaries."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    # Split by double-newline first (paragraphs)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for p in paragraphs:
        plen = len(p) + 2  # +2 for the \n\n separator
        if current and current_len + plen > MAX_CHUNK_CHARS:
            chunks.append("\n\n".join(current))
            # Overlap: keep last paragraph
            if current and len(current[-1]) <= CHUNK_OVERLAP * 2:
                current = [current[-1]]
                current_len = len(current[-1]) + 2
            else:
                current = []
                current_len = 0
        current.append(p)
        current_len += plen

    if current:
        chunks.append("\n\n".join(current))

    return chunks


# --------------------------------------------------------------------------
# Deterministic chunk ID for idempotent upsert
# --------------------------------------------------------------------------
def chunk_id(source_path: str, chunk_idx: int) -> str:
    h = hashlib.sha256(f"sidix:{source_path}:{chunk_idx}".encode()).hexdigest()
    # UUID format
    return str(uuid.UUID(h[:32]))


# --------------------------------------------------------------------------
# Main ingest
# --------------------------------------------------------------------------
async def main():
    from services.embedding import embed_text, embed_sparse_document
    from services.vector_memory import _get_client, ensure_collection, _col
    from qdrant_client.models import PointStruct

    if not KB_ROOT.exists():
        print(f"FATAL: {KB_ROOT} not mounted. Check docker-compose volume.")
        sys.exit(1)

    md_files = sorted(KB_ROOT.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files under {KB_ROOT}")
    if not md_files:
        print("Nothing to ingest.")
        return

    await ensure_collection(CORE_BRAIN_ID)
    client = await _get_client()
    col_name = _col(CORE_BRAIN_ID)

    # Stats
    stats = {
        "files": 0,
        "files_skipped_empty": 0,
        "chunks_total": 0,
        "chunks_upserted": 0,
        "embed_failures": 0,
        "by_bucket": {},
    }

    started = time.time()
    BATCH_SIZE = 20

    for fpath in md_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  [skip] read failed {fpath}: {e}")
            stats["files_skipped_empty"] += 1
            continue

        if not text.strip():
            stats["files_skipped_empty"] += 1
            continue

        rel_path = str(fpath.relative_to(KB_ROOT))
        bucket = detect_bucket(fpath)
        chunks = chunk_markdown(text)
        if not chunks:
            stats["files_skipped_empty"] += 1
            continue

        stats["files"] += 1
        stats["chunks_total"] += len(chunks)
        stats["by_bucket"].setdefault(bucket, 0)
        stats["by_bucket"][bucket] += len(chunks)

        # Build points in batches
        points: list[PointStruct] = []
        for idx, chunk in enumerate(chunks):
            try:
                dense = await embed_text(chunk)
                sparse = await embed_sparse_document(chunk)
            except Exception as e:
                print(f"  [embed-fail] {rel_path} chunk {idx}: {e}")
                stats["embed_failures"] += 1
                continue

            vec: dict = {"dense": dense}
            if sparse is not None:
                vec["sparse"] = sparse

            points.append(PointStruct(
                id=chunk_id(rel_path, idx),
                vector=vec,
                payload={
                    "agent_id": CORE_BRAIN_ID,
                    "tenant_id": SYSTEM_TENANT,
                    "bucket": bucket,
                    "source": "sidix:brain",
                    "source_path": rel_path,
                    "chunk_index": idx,
                    "chunk_total": len(chunks),
                    "chunk_text": chunk,
                    "user_message": "(inherited knowledge)",
                    "assistant_message": chunk,
                    "is_knowledge": True,
                    "ingested_at": int(time.time()),
                },
            ))

            if len(points) >= BATCH_SIZE:
                await client.upsert(collection_name=col_name, points=points)
                stats["chunks_upserted"] += len(points)
                points = []

        if points:
            await client.upsert(collection_name=col_name, points=points)
            stats["chunks_upserted"] += len(points)

        if stats["files"] % 10 == 0:
            print(f"  ... {stats['files']}/{len(md_files)} files | "
                  f"{stats['chunks_upserted']} chunks | "
                  f"{int(time.time() - started)}s")

    # Aspirations JSONL — if file is mounted (alternative path)
    asp_paths = [
        Path("/opt/sidix_kb/aspirations/induction.jsonl"),  # if mounted
    ]
    for asp in asp_paths:
        if asp.exists():
            print(f"\nIngesting aspirations from {asp}...")
            with asp.open() as f:
                for idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    content = row.get("content") or row.get("text") or json.dumps(row, ensure_ascii=False)
                    try:
                        dense = await embed_text(content)
                        sparse = await embed_sparse_document(content)
                    except Exception:
                        continue
                    vec = {"dense": dense}
                    if sparse is not None:
                        vec["sparse"] = sparse
                    await client.upsert(collection_name=col_name, points=[PointStruct(
                        id=chunk_id(f"aspirations:{asp.name}", idx),
                        vector=vec,
                        payload={
                            "agent_id": CORE_BRAIN_ID,
                            "tenant_id": SYSTEM_TENANT,
                            "bucket": "aspirations",
                            "source": "sidix:aspirations",
                            "source_path": str(asp),
                            "chunk_index": idx,
                            "chunk_text": content,
                            "user_message": "(aspiration)",
                            "assistant_message": content,
                            "is_knowledge": True,
                            "ingested_at": int(time.time()),
                        },
                    )])
                    stats["chunks_upserted"] += 1
                    stats["by_bucket"].setdefault("aspirations", 0)
                    stats["by_bucket"]["aspirations"] += 1

    elapsed = time.time() - started
    print("\n" + "=" * 60)
    print(f"SPRINT 1 INGEST COMPLETE in {elapsed:.0f}s")
    print("=" * 60)
    print(f"Files processed   : {stats['files']}")
    print(f"Files skipped     : {stats['files_skipped_empty']}")
    print(f"Chunks total      : {stats['chunks_total']}")
    print(f"Chunks upserted   : {stats['chunks_upserted']}")
    print(f"Embed failures    : {stats['embed_failures']}")
    print(f"Throughput        : {stats['chunks_upserted']/elapsed:.1f} chunks/sec")
    print(f"\nBy bucket:")
    for b in sorted(stats["by_bucket"]):
        print(f"  {b:25s} {stats['by_bucket'][b]:5d} chunks")


if __name__ == "__main__":
    asyncio.run(main())
