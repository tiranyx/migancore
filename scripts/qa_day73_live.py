"""Day 73 live QA — verify tool_router + onamix end-to-end.

Usage:
    cd /opt/ado && PYTHONPATH=api python3 scripts/qa_day73_live.py
"""
import asyncio
import sys

sys.path.insert(0, "api")

from services.tool_executor import _onamix_search, ToolContext  # noqa: E402
from services.tool_router import route_tools  # noqa: E402


async def main():
    failures = 0

    print("=== TEST 1: tool_router keyword path (Indonesian) ===")
    available = [
        "onamix_search", "onamix_get", "generate_chart", "read_pdf",
        "translate_text", "memory_write", "memory_search", "generate_image",
        "run_python", "calculate",
    ]
    selected = await route_tools("cari berita teknologi AI terbaru", available)
    print(f"  query='cari berita...' -> selected={selected}")
    ok = "onamix_search" in selected and len(selected) < len(available)
    print(f"  [{'PASS' if ok else 'FAIL'}] onamix_search in selected, count < available")
    failures += 0 if ok else 1

    print()
    print("=== TEST 2: tool_router image keyword ===")
    selected = await route_tools("buat gambar kucing oren", available)
    print(f"  selected={selected}")
    ok = "generate_image" in selected
    print(f"  [{'PASS' if ok else 'FAIL'}] generate_image in selected")
    failures += 0 if ok else 1

    print()
    print("=== TEST 3: tool_router casual reflex path ===")
    selected = await route_tools("hello apa kabar", available)
    print(f"  selected={selected}")
    ok = selected == []
    print(f"  [{'PASS' if ok else 'FAIL'}] casual chat returns zero tools")
    failures += 0 if ok else 1

    print()
    print("=== TEST 4: onamix_search DDG happy path ===")
    ctx = ToolContext(tenant_id="qa", agent_id="core_brain")
    r = await _onamix_search(
        {"query": "OpenAI GPT-5 release 2026", "engine": "ddg", "limit": 3}, ctx
    )
    print(f"  count={r['count']} transport={r['transport']}")
    if r["count"]:
        print(f"  first: {r['results'][0].get('title', '')[:70]}")
    ok = r["count"] > 0
    print(f"  [{'PASS' if ok else 'FAIL'}] DDG returned results")
    failures += 0 if ok else 1

    print()
    print("=== TEST 5: onamix_search invalid engine -> coerced ddg ===")
    r = await _onamix_search({"query": "kucing", "engine": "xyz_fake", "limit": 2}, ctx)
    ok = r["engine"] == "ddg"
    print(f"  engine_resolved={r['engine']} count={r['count']}")
    print(f"  [{'PASS' if ok else 'FAIL'}] invalid engine coerced to ddg")
    failures += 0 if ok else 1

    print()
    print("=== TEST 6: wikipedia engine direct API ===")
    r = await _onamix_search({"query": "Soekarno", "engine": "wikipedia", "limit": 1}, ctx)
    has_content = bool(r.get("answer_content"))
    print(f"  source={r.get('source')} has_content={has_content}")
    if has_content:
        print(f"  content preview: {r['answer_content'][:120]}")
    ok = has_content
    print(f"  [{'PASS' if ok else 'FAIL'}] wikipedia returned content extract")
    failures += 0 if ok else 1

    print()
    print(f"=== SUMMARY: {6 - failures}/6 PASS, {failures} FAIL ===")
    return failures


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
