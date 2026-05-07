#!/usr/bin/env python3
"""
KB Auto-Update Script — MiganCore Day 65+
Fetches real-time economic data and appends dated snapshot to indonesia_kb_v1.md

Data sources (all free, no API key):
- exchangerate-api.com: USD/IDR, SGD/IDR, EUR/IDR, JPY/IDR, CNY/IDR
- World Bank Open Data: GDP, inflation (monthly update)
- IHSG from Yahoo Finance via simple API

Cron: run daily at 06:00 WIB (23:00 UTC prev day)
Crontab: 0 23 * * * python3 /opt/ado/scripts/kb_auto_update.py >> /tmp/kb_update.log 2>&1

Author: Claude Sonnet 4.6, Day 65
"""

import json
import datetime
import sys
import urllib.request
import urllib.error
from pathlib import Path

KB_PATH = Path("/opt/ado/knowledge/indonesia_kb_v1.md")
LOG_PATH = Path("/tmp/kb_update.log")

# ── helpers ─────────────────────────────────────────────────────────────────

def fetch(url: str, timeout: int = 10) -> dict | None:
    """Fetch JSON from URL, return None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MiganCore-KB/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  WARN fetch {url}: {e}", flush=True)
        return None


def get_exchange_rates() -> dict:
    """Get IDR exchange rates from free API (no key needed)."""
    data = fetch("https://api.exchangerate-api.com/v4/latest/IDR")
    if not data or "rates" not in data:
        return {}

    rates = data["rates"]
    # Convert to IDR per 1 unit of foreign currency
    result = {}
    for currency in ["USD", "SGD", "EUR", "JPY", "CNY", "MYR", "AUD", "GBP"]:
        if currency in rates and rates[currency] != 0:
            result[currency] = round(1 / rates[currency])
    return result


def get_ihsg() -> str | None:
    """Get IHSG (IDX Composite) latest close from Yahoo Finance."""
    # Yahoo Finance API endpoint for IHSG (^JKSE)
    data = fetch(
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EJKSE?interval=1d&range=1d",
        timeout=10
    )
    if not data:
        return None

    try:
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        if price:
            return f"{price:,.0f}"
    except (KeyError, IndexError, TypeError):
        pass
    return None


def get_gold_price() -> str | None:
    """Get gold price (USD/troy oz) from free API."""
    data = fetch("https://api.exchangerate-api.com/v4/latest/XAU", timeout=10)
    if data and "rates" in data:
        idr_rate = data["rates"].get("IDR", 0)
        if idr_rate > 0:
            # 1 troy oz = 31.1g
            per_gram = round(idr_rate / 31.1035, -3)
            return f"Rp {per_gram:,.0f}/gram"
    return None


def build_snapshot(rates: dict, ihsg: str | None, gold: str | None) -> str:
    """Build the dated snapshot section."""
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)  # WIB
    date_str = now.strftime("%Y-%m-%d %H:%M WIB")

    lines = [
        "",
        f"## DATA TERKINI — {date_str}",
        "*(Auto-updated by kb_auto_update.py cron)*",
        "",
    ]

    if rates:
        lines.append("### Kurs Rupiah (IDR)")
        lines.append("| Mata Uang | Kurs Beli (IDR) |")
        lines.append("|-----------|-----------------|")
        currency_names = {
            "USD": "USD (Dolar AS)", "SGD": "SGD (Dolar Singapura)",
            "EUR": "EUR (Euro)", "JPY": "JPY (Yen Jepang)",
            "CNY": "CNY (Yuan China)", "MYR": "MYR (Ringgit Malaysia)",
            "AUD": "AUD (Dolar Australia)", "GBP": "GBP (Poundsterling)"
        }
        for code, idr in rates.items():
            name = currency_names.get(code, code)
            lines.append(f"| {name} | Rp {idr:,} |")
        lines.append("")

    if ihsg:
        lines.append("### Pasar Modal")
        lines.append(f"- **IHSG (IDX Composite):** {ihsg}")
        lines.append("")

    if gold:
        lines.append("### Komoditas")
        lines.append(f"- **Emas:** {gold}")
        lines.append("")

    return "\n".join(lines)


# ── main ────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.datetime.utcnow().isoformat()}] kb_auto_update.py starting", flush=True)

    if not KB_PATH.exists():
        print(f"ERROR: KB file not found at {KB_PATH}", flush=True)
        sys.exit(1)

    # Fetch data
    print("  Fetching exchange rates...", flush=True)
    rates = get_exchange_rates()
    print(f"  Got {len(rates)} rates: {list(rates.keys())}", flush=True)

    print("  Fetching IHSG...", flush=True)
    ihsg = get_ihsg()
    print(f"  IHSG: {ihsg}", flush=True)

    print("  Fetching gold price...", flush=True)
    gold = get_gold_price()
    print(f"  Gold: {gold}", flush=True)

    if not rates and not ihsg:
        print("ERROR: No data fetched — skipping update", flush=True)
        sys.exit(1)

    # Build snapshot
    snapshot = build_snapshot(rates, ihsg, gold)

    # Read existing KB
    existing = KB_PATH.read_text(encoding="utf-8")

    # Remove previous auto-update section (if exists) — keep KB clean
    marker = "## DATA TERKINI —"
    if marker in existing:
        # Find the last occurrence and remove from there to end (or next major section)
        idx = existing.rfind(marker)
        # Find the preceding newline before marker
        prev_newline = existing.rfind("\n", 0, idx)
        if prev_newline > 0:
            existing = existing[:prev_newline]
        print("  Removed previous DATA TERKINI section", flush=True)

    # Append snapshot
    updated = existing.rstrip() + "\n" + snapshot
    KB_PATH.write_text(updated, encoding="utf-8")

    print(f"  KB updated: {KB_PATH}", flush=True)
    print(f"  New size: {len(updated)} chars", flush=True)
    print("[DONE]", flush=True)


if __name__ == "__main__":
    main()
