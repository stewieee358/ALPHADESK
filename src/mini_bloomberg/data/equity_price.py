"""
Price history router: FMP for US, OpenBB fallback for non-US.
"""

from mini_bloomberg.core.errors import DataSourceError
from mini_bloomberg.core.ticker import Ticker
from mini_bloomberg.data.providers import fmp_provider, openbb_provider, tushare_provider
from mini_bloomberg.data.schemas import PriceHistory


def get_price_history(ticker: Ticker, days: int = 365) -> PriceHistory:
    if ticker.is_china:
        return tushare_provider.get_price_history(ticker, days=days)
    if ticker.is_us:
        try:
            history = fmp_provider.get_price_history(ticker, limit=days)
            if not history.bars:
                raise DataSourceError(f"FMP: no price history for {ticker}")
            return history.model_copy(update={
                "bars": sorted(history.bars, key=lambda bar: bar.date), "source": "FMP",
            })
        except DataSourceError:
            pass

    try:
        history = openbb_provider.get_price_history(ticker, days=days)
        if not history.bars:
            raise DataSourceError(f"OpenBB: no price history for {ticker}")
        return history.model_copy(update={
            "bars": sorted(history.bars, key=lambda bar: bar.date), "source": "OpenBB/yfinance",
        })
    except DataSourceError:
        raise
    except Exception as e:
        raise DataSourceError(f"All price providers failed for {ticker}: {e}") from e
