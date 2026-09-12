"""
FMP (Financial Modeling Prep) data provider.
All endpoints use /stable/ with symbol as a query parameter.

Working free-tier endpoints (confirmed in Milestone 1 probe):
  /stable/income-statement        ?symbol=&limit=
  /stable/balance-sheet-statement ?symbol=&limit=
  /stable/cash-flow-statement     ?symbol=&limit=
  /stable/historical-price-eod/full ?symbol=&limit=
  /stable/price-target-consensus  ?symbol=
  /stable/search-symbol           ?query=   (note: uses 'query', not 'symbol')

NOT available on free tier:
  /stable/profile                 → empty response
  /stable/analyst-estimates       → 400
  /stable/analyst-stock-recommendations → 404
"""

from datetime import datetime, timezone
import httpx

from mini_bloomberg.config import get_settings
from mini_bloomberg.core.cache import cached
from mini_bloomberg.core.errors import DataSourceError, RateLimitError
from mini_bloomberg.core.ticker import Ticker
from mini_bloomberg.data.schemas import (
    BalanceSheet,
    CashFlow,
    IncomeStatement,
    PriceBar,
    PriceHistory,
    PriceTarget,
)


def _get(endpoint: str, params: dict) -> list | dict:
    settings = get_settings()
    params["apikey"] = settings.fmp_api_key
    url = f"{settings.fmp_base_url}/{endpoint}"
    try:
        r = httpx.get(url, params=params, timeout=15)
        if r.status_code == 429:
            raise RateLimitError("FMP rate limit hit (429)")
        if r.status_code == 400:
            raise DataSourceError(f"FMP bad request for {endpoint}: {r.text[:200]}")
        r.raise_for_status()
        return r.json()
    except (RateLimitError, DataSourceError):
        raise
    except httpx.HTTPError as e:
        raise DataSourceError(f"FMP HTTP error on {endpoint}: {e}") from e


# ─── Financials ───────────────────────────────────────────────────────────────

@cached(ttl=get_settings().cache_ttl_seconds)
def get_income_statements(ticker: Ticker, limit: int = 4) -> list[IncomeStatement]:
    data = _get("income-statement", {"symbol": ticker.fmp_symbol, "limit": limit})
    if not isinstance(data, list) or not data:
        raise DataSourceError(f"FMP: no income statement data for {ticker.symbol}")
    return [IncomeStatement.from_fmp(r) for r in data]


@cached(ttl=get_settings().cache_ttl_seconds)
def get_balance_sheets(ticker: Ticker, limit: int = 4) -> list[BalanceSheet]:
    data = _get("balance-sheet-statement", {"symbol": ticker.fmp_symbol, "limit": limit})
    if not isinstance(data, list) or not data:
        raise DataSourceError(f"FMP: no balance sheet data for {ticker.symbol}")
    return [BalanceSheet.from_fmp(r) for r in data]


@cached(ttl=get_settings().cache_ttl_seconds)
def get_cash_flows(ticker: Ticker, limit: int = 4) -> list[CashFlow]:
    data = _get("cash-flow-statement", {"symbol": ticker.fmp_symbol, "limit": limit})
    if not isinstance(data, list) or not data:
        raise DataSourceError(f"FMP: no cash flow data for {ticker.symbol}")
    return [CashFlow.from_fmp(r) for r in data]


# ─── Price history ────────────────────────────────────────────────────────────

@cached(ttl=3600)  # 1-hour TTL for price data
def get_price_history(ticker: Ticker, limit: int = 365) -> PriceHistory:
    data = _get("historical-price-eod/full", {"symbol": ticker.fmp_symbol, "limit": limit})
    if isinstance(data, dict):
        bars_raw = data.get("historical", [])
    elif isinstance(data, list):
        bars_raw = data
    else:
        bars_raw = []
    if not bars_raw:
        raise DataSourceError(f"FMP: no price history for {ticker.symbol}")
    bars = [PriceBar.from_fmp(b) for b in bars_raw]
    return PriceHistory(symbol=ticker.symbol, bars=bars, source="FMP",
                        fetched_at=datetime.now(timezone.utc).isoformat())


# ─── Analyst / price targets ──────────────────────────────────────────────────

@cached(ttl=get_settings().cache_ttl_seconds)
def get_price_target(ticker: Ticker) -> PriceTarget:
    data = _get("price-target-consensus", {"symbol": ticker.fmp_symbol})
    rec = data[0] if isinstance(data, list) and data else data
    if not isinstance(rec, dict) or not rec:
        raise DataSourceError(f"FMP: no price target data for {ticker.symbol}")
    return PriceTarget.from_fmp(rec)


# ─── Ticker search ────────────────────────────────────────────────────────────

def search_symbol(query: str) -> list[dict]:
    """Returns list of {symbol, name, currency, exchangeFullName, exchange}."""
    try:
        data = _get("search-symbol", {"query": query})
        return data if isinstance(data, list) else []
    except DataSourceError:
        return []
