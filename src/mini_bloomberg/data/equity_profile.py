"""
Profile router: OpenBB for all tickers (FMP /stable/profile empty on free tier).
Falls back to a DataSourceError if OpenBB also fails.
"""

from mini_bloomberg.core.errors import DataSourceError
from mini_bloomberg.core.ticker import Ticker
from mini_bloomberg.data.providers import openbb_provider, tushare_provider
from mini_bloomberg.data.schemas import CompanyProfile


def get_profile(ticker: Ticker) -> CompanyProfile:
    """
    Fetch company profile for any ticker.
    Primary: OpenBB/yfinance (works for US and most non-US).
    TODO: wire in FMP profile if/when a paid tier key is available.
    """
    if ticker.is_china:
        return tushare_provider.get_profile(ticker)
    try:
        return openbb_provider.get_profile(ticker)
    except DataSourceError:
        raise
    except Exception as e:
        raise DataSourceError(f"All profile providers failed for {ticker}: {e}") from e
