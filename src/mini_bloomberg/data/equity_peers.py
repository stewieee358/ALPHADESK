"""
Peers router for COMP.
- Peer list: FMP /stable/stock-peers (returns symbol + name + price + mktCap)
- Fundamentals per peer: FMP income/balance statements fetched concurrently via httpx async
- OpenBB/yfinance fallback: used when FMP returns 402 (rate limit / tier restriction)
"""

import asyncio
import concurrent.futures
from typing import Optional

import httpx

from mini_bloomberg.config import get_settings
from mini_bloomberg.core.cache import cached
from mini_bloomberg.core.errors import DataSourceError
from mini_bloomberg.core.ticker import Ticker
from mini_bloomberg.data.providers import openbb_provider, tushare_provider
from mini_bloomberg.data.schemas import Comparables, PeerProfile


def get_comparables(ticker: Ticker) -> Comparables:
    if ticker.is_china:
        return tushare_provider.get_comparables(ticker)
    peers_raw = _get_peer_list(ticker)
    if not peers_raw:
        return Comparables(symbol=ticker.symbol, peers=[])

    capped = peers_raw[:8]
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # FastAPI context: run coroutine in a fresh thread with its own event loop
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            peers = pool.submit(asyncio.run, _enrich_peers_async(capped)).result()
    else:
        peers = asyncio.run(_enrich_peers_async(capped))

    # OpenBB fallback for peers where FMP returned 402 (revenue is still None)
    raw_by_sym = {p["symbol"]: p for p in capped}
    peers = [
        _openbb_enrich_peer(p, raw_by_sym[p.symbol]) if p.revenue is None else p
        for p in peers
    ]

    return Comparables(symbol=ticker.symbol, peers=peers)


@cached(ttl=86400)
def _get_peer_list(ticker: Ticker) -> list[dict]:
    """FMP /stable/stock-peers — returns [{symbol, companyName, price, mktCap}]."""
    settings = get_settings()
    try:
        r = httpx.get(
            f"{settings.fmp_base_url}/stock-peers",
            params={"symbol": ticker.fmp_symbol, "apikey": settings.fmp_api_key},
            timeout=15,
        )
        if r.status_code != 200:
            return []
        return r.json() if isinstance(r.json(), list) else []
    except Exception:
        return []


async def _enrich_peers_async(peers_raw: list[dict]) -> list[PeerProfile]:
    """Fetch income + balance + cash flow data for each peer concurrently via FMP."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=20) as client:
        tasks = [_enrich_peer(client, settings, p) for p in peers_raw]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, PeerProfile)]


async def _enrich_peer(client: httpx.AsyncClient, settings, peer: dict) -> Optional[PeerProfile]:
    sym = peer["symbol"]
    key = settings.fmp_api_key
    base = settings.fmp_base_url

    async def _get(endpoint: str) -> list:
        try:
            r = await client.get(f"{base}/{endpoint}", params={"symbol": sym, "apikey": key, "limit": 1})
            if r.status_code == 200:
                data = r.json()
                return data if isinstance(data, list) else []
        except Exception:
            pass
        return []

    # Fetch income, balance, and cash flow in parallel
    inc_list, bal_list, cf_list = await asyncio.gather(
        _get("income-statement"),
        _get("balance-sheet-statement"),
        _get("cash-flow-statement"),
    )

    price      = peer.get("price")
    mktcap     = peer.get("mktCap")
    revenue    = gross_margin = net_margin = op_margin = ebitda = total_debt = None
    pe_ratio   = pb_ratio = fcf_yield = None

    if inc_list:
        inc    = inc_list[0]
        revenue = inc.get("revenue")
        gp     = inc.get("grossProfit")
        ni     = inc.get("netIncome")
        oi     = inc.get("operatingIncome")
        ebitda = inc.get("ebitda")
        eps_d  = inc.get("epsDiluted")
        if revenue:
            gross_margin = (gp / revenue * 100) if gp is not None else None
            net_margin   = (ni / revenue * 100) if ni is not None else None
            op_margin    = (oi / revenue * 100) if oi is not None else None
        if price and eps_d and eps_d != 0:
            pe_ratio = round(price / eps_d, 2)

    if bal_list:
        b = bal_list[0]
        total_debt = b.get("totalDebt")
        equity = b.get("totalStockholdersEquity") or b.get("totalEquity")
        if mktcap and equity and equity != 0:
            pb_ratio = round(mktcap / equity, 2)

    if cf_list and mktcap and mktcap != 0:
        fcf = cf_list[0].get("freeCashFlow")
        if fcf is not None:
            fcf_yield = round(fcf / mktcap, 4)

    return PeerProfile(
        symbol=sym,
        name=peer.get("companyName"),
        market_cap=mktcap,
        pe_ratio=pe_ratio,
        pb_ratio=pb_ratio,
        fcf_yield=fcf_yield,
        revenue=revenue,
        gross_margin=gross_margin,
        net_margin=net_margin,
        operating_margin=op_margin,
        ebitda=ebitda,
        total_debt=total_debt,
        currency="USD",  # FMP peer list is US-centric; TODO non-US currency
    )


def _openbb_enrich_peer(peer: PeerProfile, raw: dict) -> PeerProfile:
    """Fallback: fetch fundamentals from yfinance for one peer when FMP returns 402."""
    try:
        obb = openbb_provider._obb()
        sym = raw["symbol"]
        price  = raw.get("price")
        mktcap = raw.get("mktCap")

        def _yf_all(result) -> list[dict]:
            return openbb_provider._all(result)

        inc_raw = _yf_all(obb.equity.fundamental.income(
            symbol=sym, provider="yfinance", period="annual", limit=2
        ))
        # Drop forward/TTM rows with no actual revenue
        inc_raw = [r for r in inc_raw if r.get("total_revenue") or r.get("net_income") or r.get("gross_profit")][:1]

        bal_raw = _yf_all(obb.equity.fundamental.balance(
            symbol=sym, provider="yfinance", period="annual", limit=1
        ))

        cf_raw = _yf_all(obb.equity.fundamental.cash(
            symbol=sym, provider="yfinance", period="annual", limit=1
        ))

        revenue = gross_margin = net_margin = op_margin = ebitda = total_debt = None
        pe_ratio = pb_ratio = fcf_yield = None

        if inc_raw:
            inc = inc_raw[0]
            revenue = inc.get("total_revenue") or inc.get("revenue") or inc.get("operating_revenue")
            gp  = inc.get("gross_profit")
            ni  = inc.get("net_income") or inc.get("net_income_continuous_operations")
            oi  = inc.get("operating_income") or inc.get("ebit")
            ebitda = inc.get("ebitda") or inc.get("normalized_ebitda")
            eps_d = inc.get("diluted_earnings_per_share") or inc.get("eps_diluted")
            if revenue:
                gross_margin = (gp / revenue * 100) if gp is not None else None
                net_margin   = (ni / revenue * 100) if ni is not None else None
                op_margin    = (oi / revenue * 100) if oi is not None else None
            if price and eps_d and eps_d != 0:
                pe_ratio = round(price / eps_d, 2)

        if bal_raw:
            b = bal_raw[0]
            total_debt = b.get("total_debt")
            equity = (
                b.get("total_common_equity")
                or b.get("common_stock_equity")
                or b.get("total_stockholder_equity")
            )
            if mktcap and equity and equity != 0:
                pb_ratio = round(mktcap / equity, 2)

        if cf_raw and mktcap and mktcap != 0:
            cf = cf_raw[0]
            fcf = cf.get("free_cash_flow")
            if fcf is not None:
                fcf_yield = round(fcf / mktcap, 4)

        return PeerProfile(
            symbol=peer.symbol,
            name=peer.name,
            market_cap=peer.market_cap,
            pe_ratio=pe_ratio,
            pb_ratio=pb_ratio,
            fcf_yield=fcf_yield,
            revenue=revenue,
            gross_margin=gross_margin,
            net_margin=net_margin,
            operating_margin=op_margin,
            ebitda=ebitda,
            total_debt=total_debt,
            currency="USD",
        )
    except Exception:
        return peer  # return partially-populated peer if fallback also fails
