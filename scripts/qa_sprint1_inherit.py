#!/usr/bin/env python3
"""
Sprint 1 QA — Verify SIDIX knowledge inherited & searchable.

After ingest_sidix_brain.py finishes, this script probes Qdrant with
representative queries from each bucket and checks the brain can retrieve
relevant SIDIX content.

Run INSIDE api container:
    docker exec -i ado-api-1 python3 - < scripts/qa_sprint1_inherit.py

Or after deploy:
    docker exec ado-api-1 python3 /app/workspace/qa_sprint1_inherit.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")

CORE_BRAIN_ID = "cb3ebd3b-4c31-4af7-8470-25c2011c0974"

# 8 probes — one per major bucket to verify inheritance
PROBES = [
    ("ilm:coding",          "roadmap belajar machine learning"),
    ("ilm:coding",          "apa itu data structures and algorithms"),
    ("ilm:coding",          "Python topics untuk pemula"),
    ("ilm:coding",          "Docker dan containerization basics"),
    ("ilm:glossary",        "technical glossary vector embedding"),
    ("ilm:glossary",        "islamic concept qalb dalam ADO"),
    ("ilm:curriculum",      "structured learning path roadmap"),
    ("maqashid",            "purpose intent framework"),
]


async def main():
    from services.vector_memory import search_semantic, _get_client, _col

    client = await _get_client()
    col_name = _col(CORE_BRAIN_ID)

    # 1. Collection stats
    print("=" * 70)
    print("SPRINT 1 QA — SIDIX KNOWLEDGE INHERIT VERIFICATION")
    print("=" * 70)
    info = await client.get_collection(col_name)
    print(f"Collection      : {col_name}")
    print(f"Points indexed  : {info.points_count}")
    print(f"Vectors total   : {info.vectors_count if hasattr(info, 'vectors_count') else info.points_count}")
    print()

    # 2. Sample bucket distribution (scroll + count)
    print("Bucket distribution (sample first 500 points):")
    scroll_result, _ = await client.scroll(
        collection_name=col_name,
        limit=500,
        with_payload=True,
        with_vectors=False,
    )
    by_bucket = {}
    by_source = {}
    is_knowledge_count = 0
    for p in scroll_result:
        b = p.payload.get("bucket", "(none)")
        s = p.payload.get("source", "(none)")
        by_bucket[b] = by_bucket.get(b, 0) + 1
        by_source[s] = by_source.get(s, 0) + 1
        if p.payload.get("is_knowledge"):
            is_knowledge_count += 1
    for b in sorted(by_bucket):
        print(f"  {b:25s} {by_bucket[b]:5d}")
    print(f"  is_knowledge flag    : {is_knowledge_count}/500")
    print(f"  sources              : {by_source}")
    print()

    # 3. Probe each bucket
    print("Probe semantic search:")
    print("=" * 70)
    passed = 0
    for expected_bucket, query in PROBES:
        print(f"\nQ: '{query}' (expect bucket={expected_bucket})")
        hits = await search_semantic(CORE_BRAIN_ID, query, top_k=3)
        if not hits:
            print("  [FAIL] no hits")
            continue
        # Inspect top hit
        top = hits[0]
        b = top.get("bucket", "?")
        src = top.get("source_path", "?")
        score = top.get("_retrieval_score", 0)
        chunk = (top.get("chunk_text") or top.get("assistant_message", ""))[:200]
        bucket_match = "✓" if expected_bucket in b else "✗"
        knowledge_match = "✓" if top.get("is_knowledge") else "✗"
        print(f"  Top hit: bucket={b} [{bucket_match}] knowledge=[{knowledge_match}] score={score:.3f}")
        print(f"          source={src}")
        print(f"          text  ={chunk}")
        if top.get("is_knowledge") and expected_bucket in b:
            passed += 1

    print()
    print("=" * 70)
    print(f"SUMMARY: {passed}/{len(PROBES)} probes returned correct-bucket knowledge")
    print("=" * 70)
    return 0 if passed >= len(PROBES) - 1 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
