"""Day 73 panel live QA.

Verifies the "Jurnal & Proposal Migan" admin surface without mutating data.

Run on VPS:
    cd /opt/ado
    ADMIN_SECRET_KEY=$(grep '^ADMIN_SECRET_KEY=' .env | cut -d= -f2-) \
      python3 scripts/qa_day73_panel_live.py

Optional:
    python3 scripts/qa_day73_panel_live.py --base http://127.0.0.1:18000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def fetch_json(url: str, admin_key: str | None = None) -> tuple[int, dict]:
    headers = {}
    if admin_key:
        headers["X-Admin-Key"] = admin_key
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"HTTP {exc.code} for {url}: {body[:300]}") from exc


def fetch_text(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"HTTP {exc.code} for {url}: {body[:300]}") from exc


def check(name: str, ok: bool, detail: str = "") -> int:
    label = "PASS" if ok else "FAIL"
    print(f"[{label}] {name}{' - ' + detail if detail else ''}")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:18000")
    parser.add_argument("--frontend", default="https://app.migancore.com/backlog.html")
    parser.add_argument("--admin-key", default=os.getenv("ADMIN_SECRET_KEY", ""))
    args = parser.parse_args()

    failures = 0

    status, health = fetch_json(f"{args.base}/health")
    failures += check("health status", status == 200 and health.get("status") == "healthy", str(health))
    failures += check("model locked", health.get("model") == "migancore:0.7c", health.get("model", ""))

    status, system = fetch_json(f"{args.base}/v1/system/status")
    failures += check("system status", status == 200 and system.get("status") == "operational", str(system))
    failures += check(
        "commit metadata aligned",
        health.get("commit_sha") == system.get("commit_sha") and health.get("commit_sha") != "unknown",
        f"health={health.get('commit_sha')} system={system.get('commit_sha')}",
    )

    status, html = fetch_text(args.frontend)
    markers = [
        "REFLEKSI",
        "PROPOSAL",
        "/v1/admin/reflection/latest",
        "/v1/sandbox/proposals",
        "renderLifecycle",
        "runReadiness",
        "RUN TESTS",
        "proposeReflectionUpgrade",
        "MAKE PROPOSAL",
    ]
    failures += check("backlog page served", status == 200, args.frontend)
    failures += check("backlog panel markers", all(m in html for m in markers), ", ".join(markers))

    status, sandbox_html = fetch_text(f"{args.frontend.rsplit('/', 1)[0]}/sandbox.html")
    failures += check("sandbox page served", status == 200, f"{args.frontend.rsplit('/', 1)[0]}/sandbox.html")
    failures += check("sandbox nav has backlog", 'href="/backlog.html"' in sandbox_html, "href=/backlog.html")

    if not args.admin_key:
        failures += check("admin key available", False, "set ADMIN_SECRET_KEY")
    else:
        status, proposals = fetch_json(
            f"{args.base}/v1/sandbox/proposals?verdict=pending&limit=5",
            args.admin_key,
        )
        items = proposals.get("items") or []
        failures += check("proposal endpoint", status == 200 and isinstance(items, list), f"items={len(items)}")
        if items:
            lifecycle = items[0].get("lifecycle") or {}
            failures += check(
                "proposal lifecycle visible",
                bool(lifecycle.get("required_gates")) and "next_action" in lifecycle,
                str(lifecycle),
            )

        status, reflections = fetch_json(
            f"{args.base}/v1/admin/reflection/latest?limit=3",
            args.admin_key,
        )
        refs = reflections.get("reflections") or []
        failures += check("reflection endpoint", status == 200 and isinstance(refs, list), f"reflections={len(refs)}")

    print(f"\nSUMMARY: {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
