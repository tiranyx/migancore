#!/usr/bin/env python3
"""
Sprint 1.5 — SIDIX Brain Ingest v2 (Pencernaan-aware)
=====================================================
Day 73 | 2026-05-14 | Selection + Digestion + Absorption enhancements

UPGRADES from v1:
  SELECTION:
    - quality_score per file (high_trust/low_trust/skip)
    - SKIP_PATHS for incoming/ (raw unprocessed)
    - dedup via content hash (skip if hash already seen this run)
  DIGESTION:
    - Heading propagation: chunk text prefixed with [section path]
    - Code-block preserve: never split inside ``` ```
    - Boundary at heading transitions when possible
  ABSORPTION (richer payload):
    - heading_path: "Coding / ML / Algorithms"
    - trust_score: 0.0-1.0
    - freshness_days: from file mtime
    - language: id|en|mix
    - granularity: paragraph (sentence later)
    - source_top: first path segment (for fast filter)
    - ingested_version: "v2.0"

IDEMPOTENT: Deterministic UUID from (source_path, chunk_idx) — re-runs
upsert same IDs. Existing chunks get UPGRADED payload + re-embedded with
heading-enriched text (slightly different vectors = better topical retrieval).

Run AFTER v1 finishes — script is safe to interleave (upsert overwrites).
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, "/app")

CORE_BRAIN_ID = "cb3ebd3b-4c31-4af7-8470-25c2011c0974"
SYSTEM_TENANT = "00000000-0000-0000-0000-000000000000"

KB_ROOT = Path("/opt/sidix_kb")
MAX_CHUNK_CHARS = 1200
INGEST_VERSION = "v2.0"

# -----------------------------------------------------------------------------
# SELECTION — quality scoring + skip rules
# -----------------------------------------------------------------------------
SKIP_TOP_LEVEL = {"incoming"}  # raw, unprocessed → not ready

TRUST_SCORE_BY_TOP = {
    "coding":            0.95,  # canonical roadmaps
    "glossary":          0.95,  # definitional
    "curriculum":        0.90,
    "maqashid":          0.90,
    "research_notes":    0.80,
    "omnyx_knowledge":   0.80,
    "faq":               0.70,
    "hafidz":            0.70,
    "auto_learn":        0.40,  # work-in-progress
    "feedback_learning": 0.40,
}


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
        "research_notes":    "ilm:research",
    }.get(top, f"ilm:{top}")


def quality_score(path: Path) -> float:
    parts = path.relative_to(KB_ROOT).parts
    if parts[0] in SKIP_TOP_LEVEL:
        return 0.0
    return TRUST_SCORE_BY_TOP.get(parts[0], 0.6)


def detect_language(text: str) -> str:
    """Fast char n-gram language detect (id/en/mix)."""
    sample = text[:500].lower()
    id_markers = sum(1 for w in ("yang", "dan", "atau", "untuk", "adalah", "dengan", "dari") if w in sample)
    en_markers = sum(1 for w in ("the", "and", "or", "for", "is", "with", "from", "this") if w in sample)
    if id_markers >= 3 and id_markers > en_markers * 1.5:
        return "id"
    if en_markers >= 3 and en_markers > id_markers * 1.5:
        return "en"
    return "mix"


# -----------------------------------------------------------------------------
# DIGESTION — heading-aware + code-block-preserve chunking
# -----------------------------------------------------------------------------
def chunk_with_context(text: str) -> list[dict]:
    """Chunk markdown with heading propagation + code-block preservation."""
    chunks = []
    heading_stack: list[tuple[int, str]] = []
    buffer: list[str] = []
    buffer_chars = 0
    in_code_block = False

    def emit():
        nonlocal buffer, buffer_chars
        if not buffer:
            return
        body = "\n".join(buffer).strip()
        if not body:
            buffer = []
            buffer_chars = 0
            return
        heading_path = " / ".join(h[1] for h in heading_stack) or "(root)"
        enriched = f"[{heading_path}]\n\n{body}"
        chunks.append({
            "text": enriched,
            "raw_body": body,
            "heading_path": heading_path,
        })
        # Overlap: keep last paragraph for context continuity
        if buffer and len(buffer[-1]) <= 300:
            tail = buffer[-1]
            buffer = [tail]
            buffer_chars = len(tail) + 1
        else:
            buffer = []
            buffer_chars = 0

    for raw_line in text.split("\n"):
        line = raw_line.rstrip()

        # Code block boundary detection
        stripped = line.strip()
        if stripped.startswith("```"):
            buffer.append(line)
            buffer_chars += len(line) + 1
            in_code_block = not in_code_block
            continue

        # Inside code block — never split
        if in_code_block:
            buffer.append(line)
            buffer_chars += len(line) + 1
            continue

        # Heading detection (outside code)
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            title = line.lstrip("# ").strip()
            # Emit current buffer at heading boundary if non-trivial
            if buffer_chars > 200:
                emit()
            # Update heading stack
            heading_stack = [h for h in heading_stack if h[0] < level]
            heading_stack.append((level, title))
            # Don't include the # line in body (it's in heading_path)
            continue

        # Regular line
        buffer.append(line)
        buffer_chars += len(line) + 1

        # Emit when over budget AND not in code block AND at paragraph boundary
        if buffer_chars > MAX_CHUNK_CHARS and not in_code_block:
            # Try to split at last blank line
            if "" in buffer[-5:]:
                emit()

    # Flush remaining
    emit()
    return [c for c in chunks if c["raw_body"]]


# -----------------------------------------------------------------------------
# Deterministic chunk ID — same as v1 (idempotent upgrade)
# -----------------------------------------------------------------------------
def chunk_id(source_path: str, chunk_idx: int) -> str:
    h = hashlib.sha256(f"sidix:{source_path}:{chunk_idx}".encode()).hexdigest()
    return str(uuid.UUID(h[:32]))


# -----------------------------------------------------------------------------
# Simple entity extraction (regex-based, fast)
# -----------------------------------------------------------------------------
_ENTITY_PATTERNS = {
    "Python":     re.compile(r"\bpython\b", re.IGNORECASE),
    "JavaScript": re.compile(r"\b(javascript|js|node\.?js)\b", re.IGNORECASE),
    "Docker":     re.compile(r"\bdocker\b", re.IGNORECASE),
    "ML":         re.compile(r"\b(machine learning|ml|deep learning)\b", re.IGNORECASE),
    "Linux":      re.compile(r"\b(linux|ubuntu|debian)\b", re.IGNORECASE),
    "Git":        re.compile(r"\bgit\b", re.IGNORECASE),
    "SQL":        re.compile(r"\bsql\b", re.IGNORECASE),
    "DSA":        re.compile(r"\b(dsa|data structures? and algorithms?)\b", re.IGNORECASE),
    "AI":         re.compile(r"\b(ai|artificial intelligence)\b", re.IGNORECASE),
    "qalb":       re.compile(r"\bqalb\b", re.IGNORECASE),
    "nafs":       re.compile(r"\bnafs\b", re.IGNORECASE),
    "aql":        re.compile(r"\baql\b", re.IGNORECASE),
    "ruh":        re.compile(r"\bruh\b", re.IGNORECASE),
    "hikmah":     re.compile(r"\bhikmah\b", re.IGNORECASE),
    "ilm":        re.compile(r"\bilm\b", re.IGNORECASE),
    "Tiranyx":    re.compile(r"\btiranyx\b", re.IGNORECASE),
    "MiganCore":  re.compile(r"\b(migan(core)?|mighan-?core)\b", re.IGNORECASE),
    "SIDIX":      re.compile(r"\bsidix\b", re.IGNORECASE),
    "Qdrant":     re.compile(r"\bqdrant\b", re.IGNORECASE),
    "FastAPI":    re.compile(r"\bfast\s*api\b", re.IGNORECASE),
}


def extract_entities(text: str) -> list[str]:
    return sorted({name for name, pat in _ENTITY_PATTERNS.items() if pat.search(text)})


# -----------------------------------------------------------------------------
# Main ingest
# -----------------------------------------------------------------------------
async def main():
    from services.embedding import embed_text, embed_sparse_document
    from services.vector_memory import _get_client, ensure_collection, _col
    from qdrant_client.models import PointStruct

    if not KB_ROOT.exists():
        print(f"FATAL: {KB_ROOT} not mounted")
        sys.exit(1)

    md_files = sorted(KB_ROOT.rglob("*.md"))
    print(f"v2 Found {len(md_files)} markdown files under {KB_ROOT}", flush=True)

    await ensure_collection(CORE_BRAIN_ID)
    client = await _get_client()
    col_name = _col(CORE_BRAIN_ID)

    stats = {
        "files": 0, "files_skipped_low_quality": 0, "files_skipped_dup": 0,
        "chunks_total": 0, "chunks_upserted": 0,
        "by_bucket": {}, "by_lang": {}, "by_top": {},
    }
    seen_hashes = set()
    started = time.time()
    BATCH = 16

    for fpath in md_files:
        rel_path = str(fpath.relative_to(KB_ROOT))
        top = fpath.relative_to(KB_ROOT).parts[0]

        # SELECTION
        score = quality_score(fpath)
        if score == 0.0:
            stats["files_skipped_low_quality"] += 1
            continue

        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if not text.strip():
            continue

        # Dedup check
        content_hash = hashlib.sha256(text[:1000].encode()).hexdigest()[:16]
        if content_hash in seen_hashes:
            stats["files_skipped_dup"] += 1
            continue
        seen_hashes.add(content_hash)

        try:
            mtime = fpath.stat().st_mtime
            freshness_days = int((time.time() - mtime) / 86400)
        except Exception:
            freshness_days = -1

        bucket = detect_bucket(fpath)
        lang = detect_language(text)

        # DIGESTION
        chunks = chunk_with_context(text)
        if not chunks:
            continue

        stats["files"] += 1
        stats["chunks_total"] += len(chunks)
        stats["by_bucket"][bucket] = stats["by_bucket"].get(bucket, 0) + len(chunks)
        stats["by_lang"][lang] = stats["by_lang"].get(lang, 0) + len(chunks)
        stats["by_top"][top] = stats["by_top"].get(top, 0) + 1

        # ABSORPTION
        points = []
        for idx, ch in enumerate(chunks):
            enriched = ch["text"]
            try:
                dense = await embed_text(enriched)
                sparse = await embed_sparse_document(enriched)
            except Exception:
                continue

            vec = {"dense": dense}
            if sparse is not None:
                vec["sparse"] = sparse

            entities = extract_entities(ch["raw_body"])

            points.append(PointStruct(
                id=chunk_id(rel_path, idx),
                vector=vec,
                payload={
                    "agent_id":          CORE_BRAIN_ID,
                    "tenant_id":         SYSTEM_TENANT,
                    "bucket":            bucket,
                    "source":            "sidix:brain",
                    "source_path":       rel_path,
                    "source_top":        top,
                    "heading_path":      ch["heading_path"],
                    "chunk_index":       idx,
                    "chunk_total":       len(chunks),
                    "chunk_text":        enriched,
                    "raw_body":          ch["raw_body"],
                    # v1 compat fields (so search returns same shape):
                    "user_message":      "(inherited knowledge)",
                    "assistant_message": enriched,
                    "is_knowledge":      True,
                    # NEW v2 metadata:
                    "trust_score":       score,
                    "freshness_days":    freshness_days,
                    "language":          lang,
                    "granularity":       "paragraph",
                    "entities":          entities,
                    "ingest_version":    INGEST_VERSION,
                    "ingested_at":       int(time.time()),
                },
            ))

            if len(points) >= BATCH:
                await client.upsert(collection_name=col_name, points=points)
                stats["chunks_upserted"] += len(points)
                points = []

        if points:
            await client.upsert(collection_name=col_name, points=points)
            stats["chunks_upserted"] += len(points)

        if stats["files"] % 25 == 0:
            elapsed = int(time.time() - started)
            print(f"  ... {stats['files']} files | {stats['chunks_upserted']} chunks | {elapsed}s",
                  flush=True)

    elapsed = time.time() - started
    print("\n" + "=" * 70, flush=True)
    print(f"INGEST v2 COMPLETE in {elapsed:.0f}s", flush=True)
    print("=" * 70, flush=True)
    print(f"Files processed     : {stats['files']}", flush=True)
    print(f"Files skipped (qual): {stats['files_skipped_low_quality']}", flush=True)
    print(f"Files skipped (dup) : {stats['files_skipped_dup']}", flush=True)
    print(f"Chunks total        : {stats['chunks_total']}", flush=True)
    print(f"Chunks upserted     : {stats['chunks_upserted']}", flush=True)
    print(f"\nBy bucket:", flush=True)
    for b in sorted(stats["by_bucket"]):
        print(f"  {b:25s} {stats['by_bucket'][b]:5d}", flush=True)
    print(f"\nBy language:", flush=True)
    for l, n in stats["by_lang"].items():
        print(f"  {l:5s} {n:5d}", flush=True)
    print(f"\nBy source top-folder:", flush=True)
    for t in sorted(stats["by_top"]):
        print(f"  {t:25s} {stats['by_top'][t]:5d}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
