"""Live E2E QA — does the running brain actually apply the Innovation Engine loop?

Sends prompts via the in-container LLM service and inspects responses for
hallmarks of the doctrine: multiple options, ranking, artifacts-over-advice.
"""
import asyncio
import sys

sys.path.insert(0, "/app")

from services.ollama import OllamaClient  # type: ignore  # noqa: E402


HALLMARKS = {
    "diverge": ["opsi", "options", "alternatif", "pilihan", "1.", "2.", "3."],
    "rank": ["impact", "risk", "feasibility", "novelty", "ranking", "skor", "alignment"],
    "artifact": ["roadmap", "blueprint", "patch", "prompt", "checklist", "table", "tabel", "test", "schema"],
    "loop": ["observe", "synthesize", "diverge", "prototype", "polish", "toolify"],
}


async def probe(label: str, message: str) -> dict:
    print(f"\n=== {label} ===")
    print(f"  prompt: {message[:80]}")
    sys_prompt = (
        "[COGNITIVE SYNTHESIS - MANDATORY]\n"
        "Translate founder intent into clear concepts and an executable next step.\n\n"
        "[INNOVATION ENGINE - MANDATORY]\n"
        "Loop: OBSERVE -> SYNTHESIZE -> DIVERGE -> RANK -> PROTOTYPE -> TEST -> POLISH -> TOOLIFY -> LEARN.\n"
        "Rules: generate multiple options when exploring, rank by impact/risk/feasibility, "
        "prefer artifacts (code/roadmap/prompt/table) over abstract advice, polish important answers."
    )
    try:
        async with OllamaClient() as client:
            out = await client.chat(
                model="migancore:0.7c",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": message},
                ],
                options={"temperature": 0.7, "num_predict": 600},
            )
        text = ((out or {}).get("message") or {}).get("content") or ""
    except Exception as e:
        print(f"  ERROR: {e}")
        return {"label": label, "ok": False, "hits": {}}

    print(f"  len: {len(text)} chars")
    print(f"  preview: {text[:280]}")

    text_low = text.lower()
    hits = {k: sum(1 for kw in kws if kw in text_low) for k, kws in HALLMARKS.items()}
    print(f"  hallmark hits: {hits}")
    return {"label": label, "text": text, "hits": hits}


async def main():
    results = []
    results.append(await probe(
        "DIVERGE — strategic",
        "Aku mau bikin produk baru di atas MiganCore. Kasih ide.",
    ))
    results.append(await probe(
        "RANK + ARTIFACT — product",
        "Bantu pilih next feature MiganCore yang paling berdampak. Aku butuh artifact konkret.",
    ))
    results.append(await probe(
        "POLISH — coding",
        "Aku mau nambah endpoint /v1/proposals/rank yang ranking ide pakai impact/risk/feasibility. Approach gimana?",
    ))
    results.append(await probe(
        "DOCTRINE recall",
        "Gimana caramu mikir biar nggak cuma jawab tapi juga nghasilin inovasi?",
    ))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    pass_count = 0
    for r in results:
        if "hits" not in r or not r["hits"]:
            print(f"  [FAIL] {r['label']} — no response")
            continue
        diverge_ok = r["hits"].get("diverge", 0) >= 2
        artifact_ok = r["hits"].get("artifact", 0) >= 1
        loop_ok = r["hits"].get("loop", 0) >= 1 or r["hits"].get("rank", 0) >= 1
        ok = diverge_ok or artifact_ok or loop_ok
        marker = "PASS" if ok else "WEAK"
        print(f"  [{marker}] {r['label']:25s} diverge={r['hits'].get('diverge',0)} rank={r['hits'].get('rank',0)} artifact={r['hits'].get('artifact',0)} loop={r['hits'].get('loop',0)}")
        if ok:
            pass_count += 1
    print(f"\n  TOTAL: {pass_count}/4 probes show Innovation Engine behavior")
    return 0 if pass_count >= 3 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
