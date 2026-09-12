"""
OpenBB data provider (yfinance backend — no PAT required).
Primary source for: company profile (DES), non-US fundamentals, peers (COMP).
Fallback for: price history, analyst estimates when FMP fails.
"""

from datetime import date, datetime, timedelta, timezone

from mini_bloomberg.core.cache import cached
from mini_bloomberg.core.errors import DataSourceError
from mini_bloomberg.core.ticker import Ticker
from mini_bloomberg.data.schemas import (
    AnalystRatings,
    BalanceSheet,
    CashFlow,
    CompanyProfile,
    IncomeStatement,
    PriceBar,
    PriceHistory,
    PriceTarget,
)


def _obb():
    """Lazy import to avoid slow OpenBB startup on every module load."""
    from openbb import obb
    return obb


def _first(result) -> dict:
    """Extract first result as dict from an OBBject."""
    if not result.results:
        return {}
    item = result.results[0]
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return dict(getattr(item, "__dict__", {}))


def _all(result) -> list[dict]:
    """Extract all results as list of dicts from an OBBject."""
    out = []
    for item in result.results:
        if hasattr(item, "model_dump"):
            out.append(item.model_dump())
        else:
            out.append(dict(getattr(item, "__dict__", {})))
    return out


# ─── Profile (DES primary) ────────────────────────────────────────────────────

@cached(ttl=86400)
def get_profile(ticker: Ticker) -> CompanyProfile:
    import logging
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)  # suppress yfinance HTTP noise
    try:
        result = _obb().equity.profile(symbol=ticker.yfinance_symbol, provider="yfinance")
        raw = _first(result)
        if not raw:
            raise DataSourceError(f"OpenBB: no profile data for {ticker}")
        return CompanyProfile(
            symbol=ticker.symbol,
            name=raw.get("name"),
            exchange=raw.get("stock_exchange"),
            currency=raw.get("currency"),
            sector=raw.get("sector"),
            industry=raw.get("industry_category"),
            long_description=raw.get("long_description"),
            website=raw.get("company_url"),
            phone=raw.get("business_phone_no"),
            address=raw.get("hq_address1"),
            city=raw.get("hq_address_city"),
            state=raw.get("hq_state"),
            country=raw.get("hq_country"),
            employees=raw.get("employees"),
            market_cap=raw.get("market_cap"),
            shares_outstanding=raw.get("shares_outstanding"),
            shares_float=raw.get("shares_float"),
            dividend_yield=raw.get("dividend_yield"),
            beta=raw.get("beta"),
            issue_type=raw.get("issue_type"),
        )
    except DataSourceError:
        raise
    except Exception as e:
        raise DataSourceError(f"OpenBB profile error for {ticker}: {e}") from e


# ─── Price history (GP fallback) ──────────────────────────────────────────────

@cached(ttl=3600)
def get_price_history(ticker: Ticker, days: int = 365) -> PriceHistory:
    try:
        result = _obb().equity.price.historical(
            symbol=ticker.yfinance_symbol,
            provider="yfinance",
            start_date=(date.today() - timedelta(days=days)).isoformat(),
            end_date=date.today().isoformat(),
        )
        bars_raw = _all(result)
        if not bars_raw:
            raise DataSourceError(f"OpenBB: no price history for {ticker}")
        bars = []
        for b in bars_raw[-days:]:
            dt = b.get("date")
            date_str = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)
            bars.append(PriceBar(
                date=date_str,
                open=b.get("open"),
                high=b.get("high"),
                low=b.get("low"),
                close=b.get("close"),
                volume=b.get("volume"),
            ))
        return PriceHistory(symbol=ticker.symbol, bars=bars, source="OpenBB/yfinance",
                            fetched_at=datetime.now(timezone.utc).isoformat())
    except DataSourceError:
        raise
    except Exception as e:
        raise DataSourceError(f"OpenBB price history error for {ticker}: {e}") from e


# ─── Analyst ratings (ANR supplement) ────────────────────────────────────────

def _numeric_rating_to_label(score: float) -> str:
    """Convert yfinance 1-5 scale to text. 1=Strong Buy, 3=Hold, 5=Strong Sell."""
    if score <= 1.5:   return "Strong Buy"
    if score <= 2.5:   return "Buy"
    if score <= 3.5:   return "Hold"
    if score <= 4.5:   return "Sell"
    return "Strong Sell"


@cached(ttl=86400)
def get_analyst_ratings(ticker: Ticker) -> AnalystRatings:
    """Returns buy/hold/sell breakdown from OpenBB. May be sparse for non-US."""
    try:
        result = _obb().equity.estimates.consensus(
            symbol=ticker.yfinance_symbol,
            provider="yfinance",
        )
        raw = _first(result)
        rating = AnalystRatings(symbol=ticker.symbol)
        if raw:
            mean = raw.get("recommendation_mean") or raw.get("consensus")
            if isinstance(mean, (int, float)):
                rating.consensus_rating = _numeric_rating_to_label(mean)
            elif mean:
                rating.consensus_rating = str(mean)
            rating.num_analysts = raw.get("number_of_analysts") or raw.get("num_analysts")
            rating.strong_buy   = raw.get("strong_buy")
            rating.buy          = raw.get("buy")
            rating.hold         = raw.get("hold")
            rating.sell         = raw.get("sell")
            rating.strong_sell  = raw.get("strong_sell")
        return rating
    except Exception:
        return AnalystRatings(symbol=ticker.symbol)


# ─── Peers (COMP primary) ────────────────────────────────────────────────────

@cached(ttl=86400)
def get_peer_symbols(ticker: Ticker) -> list[str]:
    """Returns list of peer ticker symbols (plain symbol, no exchange code)."""
    try:
        result = _obb().equity.compare.peers(
            symbol=ticker.yfinance_symbol,
            provider="yfinance",
        )
        raw = _first(result)
        peers = raw.get("peers_list", []) or raw.get("peers", [])
        if isinstance(peers, str):
            peers = [p.strip() for p in peers.split(",") if p.strip()]
        return peers[:8]  # cap at 8 peers to avoid rate limits
    except Exception as e:
        raise DataSourceError(f"OpenBB peers error for {ticker}: {e}") from e
