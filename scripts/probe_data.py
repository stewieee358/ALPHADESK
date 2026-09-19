"""
Milestone 1 sanity check: probe all FMP stable endpoints + OpenBB equivalents.
Prints raw field names so we can design Pydantic schemas with confidence.

Run with:  uv run python scripts/probe_data.py
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

FMP_KEY = os.getenv("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"


# ─── FMP helpers ──────────────────────────────────────────────────────────────

def fmp_get(endpoint: str, symbol: str, extra: dict | None = None) -> list | dict | None:
    params = {"symbol": symbol, "apikey": FMP_KEY, **(extra or {})}
    try:
        r = httpx.get(f"{FMP_BASE}/{endpoint}", params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data if data else None
    except httpx.HTTPError as e:
        print(f"  [FMP /{endpoint}] HTTP error: {e}")
        return None


def print_fields(label: str, record: dict) -> None:
    print(f"\n{'=' * 64}")
    print(f"{label}  ({len(record)} fields)")
    print("=" * 64)
    for k, v in record.items():
        display = str(v)[:72] + "…" if len(str(v)) > 72 else v
        print(f"  {k:<38} {display!r}")


# ─── OpenBB helpers ───────────────────────────────────────────────────────────

def obb_get(fn, **kwargs) -> dict | None:
    try:
        result = fn(**kwargs, provider="yfinance")
        if not result.results:
            return None
        item = result.results[0]
        return item.model_dump() if hasattr(item, "model_dump") else dict(item.__dict__)
    except Exception as e:
        print(f"  [OpenBB] Error: {type(e).__name__}: {e}")
        return None


# ─── Main probe ───────────────────────────────────────────────────────────────

def main() -> None:
    symbol = "AAPL"
    print(f"ALPHADESK — Milestone 1 Full Field Probe ({symbol})")
    print(f"FMP key configured: {bool(FMP_KEY and FMP_KEY != 'your_fmp_key_here')}\n")

    if not FMP_KEY or FMP_KEY == "your_fmp_key_here":
        print("FMP_API_KEY not set — skipping FMP probes")
    else:
        # ── search-symbol (ticker lookup / identity) ──────────────────────────
        data = fmp_get("search-symbol", symbol)
        if data:
            rec = data[0] if isinstance(data, list) else data
            print_fields(f"FMP /stable/search-symbol  [{symbol}]", rec)

        # ── income-statement ──────────────────────────────────────────────────
        data = fmp_get("income-statement", symbol, {"limit": 1})
        if data:
            rec = data[0] if isinstance(data, list) else data
            print_fields(f"FMP /stable/income-statement  [{symbol}]", rec)

        # ── balance-sheet-statement ───────────────────────────────────────────
        data = fmp_get("balance-sheet-statement", symbol, {"limit": 1})
        if data:
            rec = data[0] if isinstance(data, list) else data
            print_fields(f"FMP /stable/balance-sheet-statement  [{symbol}]", rec)

        # ── cash-flow-statement ───────────────────────────────────────────────
        data = fmp_get("cash-flow-statement", symbol, {"limit": 1})
        if data:
            rec = data[0] if isinstance(data, list) else data
            print_fields(f"FMP /stable/cash-flow-statement  [{symbol}]", rec)

        # ── historical-price-eod/full (price history for GP) ─────────────────
        data = fmp_get("historical-price-eod/full", symbol, {"limit": 5})
        if data:
            # Returns {"symbol": ..., "historical": [...]}
            hist = data.get("historical", data) if isinstance(data, dict) else data
            rec = hist[0] if isinstance(hist, list) and hist else data
            if isinstance(rec, dict):
                print_fields(f"FMP /stable/historical-price-eod/full  [{symbol}]", rec)

        # ── analyst-estimates (ANR) ───────────────────────────────────────────
        data = fmp_get("analyst-estimates", symbol, {"limit": 1})
        if data:
            rec = data[0] if isinstance(data, list) else data
            print_fields(f"FMP /stable/analyst-estimates  [{symbol}]", rec)

    # ── OpenBB profile (DES — primary source since FMP profile empty on free) ─
    print(f"\n{'=' * 64}")
    print("OpenBB equity.profile (yfinance) — primary DES source")
    print("=" * 64)
    try:
        from openbb import obb
        result = obb.equity.profile(symbol=symbol, provider="yfinance")
        if result.results:
            item = result.results[0]
            rec = item.model_dump() if hasattr(item, "model_dump") else dict(item.__dict__)
            for k, v in rec.items():
                display = str(v)[:72] + "…" if len(str(v)) > 72 else v
                print(f"  {k:<38} {display!r}")
            print(f"\n  Total fields: {len(rec)}")
    except Exception as e:
        print(f"  OpenBB error: {e}")

    print(f"\n{'=' * 64}")
    print("ROUTING SUMMARY (based on free-tier FMP constraints):")
    print("=" * 64)
    print("  DES  (profile)       → OpenBB/yfinance  (FMP /stable/profile empty on free)")
    print("  FA   (financials)    → FMP /stable/income-statement + balance-sheet + cash-flow")
    print("  GP   (price)         → FMP /stable/historical-price-eod/full")
    print("  ANR  (estimates)     → FMP /stable/analyst-estimates")
    print("  COMP (peers)         → OpenBB peers list + OpenBB profile per peer")
    print("\nNon-US tickers: all routes fall back to OpenBB")


if __name__ == "__main__":
    main()
