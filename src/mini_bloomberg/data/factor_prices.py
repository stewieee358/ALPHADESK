"""Typed multi-security histories using the existing cached price router."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import math
import re

from pydantic import BaseModel, Field

from mini_bloomberg.core.errors import DataSourceError
from mini_bloomberg.core.ticker import parse_ticker, EXCHANGE_TO_YFINANCE
from mini_bloomberg.data.equity_price import get_price_history
from mini_bloomberg.data.schemas import PriceHistory


DEFAULT_SYMBOLS = "AAPL,MSFT,NVDA,AMZN,GOOGL,META,JPM,V,XOM,JNJ,PG,UNH"


class FactorPricePanel(BaseModel):
    requested_start: str
    requested_end: str
    histories: dict[str, PriceHistory]
    sources: list[dict] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def load_factor_prices(symbols: str = DEFAULT_SYMBOLS, days: int = 365,
                       start: str | None = None, end: str | None = None) -> FactorPricePanel:
    if isinstance(days, bool) or not isinstance(days, int) or not 7 <= days <= 1825:
        raise ValueError("days must be an integer between 7 and 1825 calendar days")
    today = date.today()
    stop = date.fromisoformat(end) if end else today
    begin = date.fromisoformat(start) if start else stop - timedelta(days=days)
    if begin >= stop or stop > today or (today - begin).days > 1825:
        raise ValueError("Choose start < end <= today, within the last 1825 days")
    if not isinstance(symbols, str):
        raise ValueError("symbols must be comma-separated tickers")
    tickers = []
    seen = set()
    for raw in symbols.split(','):
        ticker = parse_ticker(raw)
        if not re.fullmatch(r"[A-Z0-9.^-]{1,20}", ticker.symbol):
            raise ValueError(f"Invalid equity symbol: {ticker.symbol}")
        if not ticker.is_us and ticker.exchange_code not in EXCHANGE_TO_YFINANCE:
            raise ValueError(f"Unsupported exchange: {ticker.exchange_code}")
        canonical = ticker.yfinance_symbol
        if canonical not in seen:
            seen.add(canonical)
            tickers.append(ticker)
    if not 10 <= len(tickers) <= 50:
        raise ValueError("Market evaluation requires 10–50 unique securities (comma-separated)")

    # Request enough recent history to reach start even for an older end date.
    lookback = (today - begin).days + 7
    def fetch(ticker):
        name = str(ticker)
        try:
            history = get_price_history(ticker, days=lookback)
            bars = []
            dates_seen = set()
            for bar in history.bars:
                day = date.fromisoformat(bar.date[:10])
                if not begin <= day <= stop:
                    continue
                if day in dates_seen:
                    raise ValueError("duplicate daily observations")
                dates_seen.add(day)
                if bar.close is None or not math.isfinite(bar.close) or bar.close <= 0:
                    continue
                bars.append(bar.model_copy(update={"date": day.isoformat()}))
            bars.sort(key=lambda b: b.date)
            if len(bars) < 3:
                raise ValueError("fewer than 3 valid daily prices in requested interval")
            return name, history.model_copy(update={"bars": bars}), None
        except Exception:
            # Provider exceptions may contain URLs with credentials: keep errors local and safe.
            return name, None, "history unavailable or invalid; check provider access and date range"

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch, tickers))
    failures = [f"{name}: {error}" for name, _, error in results if error]
    if failures:
        raise DataSourceError("Market data failed (no synthetic substitution): " + "; ".join(failures))
    histories = {name: history for name, history, _ in results}
    sources = [{"security": name, "source": history.source or "Existing price router",
                "first_date": history.bars[0].date, "last_date": history.bars[-1].date,
                "bars": len(history.bars), "fetched_at": getattr(history, "fetched_at", None),
                "currency": history.currency}
               for name, history in histories.items()]
    notes = ["Online daily OHLCV, not a streaming quote feed. Existing provider cache TTL: 1 hour.",
             "Prices retain provider adjustment conventions and native currencies; adjustment consistency is not guaranteed.",
             "Selected current securities form a user-defined universe, not a survivorship-free historical universe."]
    if len({row['last_date'] for row in sources}) > 1:
        notes.append("Latest dates differ across securities; missing dates remain missing (no forward fill).")
    stale = [row['security'] for row in sources if (stop - date.fromisoformat(row['last_date'])).days > 7]
    if stale:
        notes.append("History ends over 7 calendar days before requested end: " + ", ".join(stale))
    return FactorPricePanel(requested_start=begin.isoformat(), requested_end=stop.isoformat(),
                            histories=histories, sources=sources, notes=notes)
