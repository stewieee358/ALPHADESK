"""
Analyst estimates router: FMP price-target-consensus + OpenBB buy/hold/sell.
"""

from mini_bloomberg.core.errors import DataSourceError
from mini_bloomberg.core.ticker import Ticker
from mini_bloomberg.data.providers import fmp_provider, openbb_provider, tushare_provider
from mini_bloomberg.data.schemas import AnalystRatings


def get_analyst_ratings(ticker: Ticker) -> AnalystRatings:
    if ticker.is_china:
        return tushare_provider.get_analyst_ratings(ticker)
    ratings = AnalystRatings(symbol=ticker.symbol)

    # Price targets from FMP (US only; free tier confirmed working)
    if ticker.is_us:
        try:
            pt = fmp_provider.get_price_target(ticker)
            ratings.price_target = pt
        except DataSourceError:
            pass

    # Buy/hold/sell consensus from OpenBB (works for US and some non-US)
    try:
        obb_ratings = openbb_provider.get_analyst_ratings(ticker)
        ratings.consensus_rating = obb_ratings.consensus_rating
        ratings.num_analysts     = obb_ratings.num_analysts
        ratings.strong_buy       = obb_ratings.strong_buy
        ratings.buy              = obb_ratings.buy
        ratings.hold             = obb_ratings.hold
        ratings.sell             = obb_ratings.sell
        ratings.strong_sell      = obb_ratings.strong_sell
    except Exception:
        pass  # partial data is fine for ANR

    if ratings.price_target is None and ratings.consensus_rating is None:
        raise DataSourceError(f"No analyst data available for {ticker}")

    return ratings
