"""Tushare Pro provider for mainland-China equities.

The provider maps Tushare's native data frames into ALPHADESK's common
Pydantic schemas. Credentials and an optional compatible gateway are read from
the normal application settings, so Web, CLI and notebooks use one setup.
"""

from __future__ import annotations

from datetime import date, timedelta
from statistics import median
import math

import pandas as pd

from mini_bloomberg.config import get_settings
from mini_bloomberg.core.cache import cached
from mini_bloomberg.core.errors import DataSourceError
from mini_bloomberg.core.ticker import Ticker
from mini_bloomberg.data.schemas import (
    AnalystRatings,
    BalanceSheet,
    CashFlow,
    CompanyProfile,
    Financials,
    IncomeStatement,
    PriceBar,
    PriceHistory,
    PriceTarget,
    Comparables,
    PeerProfile,
    QuarterlyFinancials,
    QuarterlyPeriod,
)


def _client():
    try:
        import tushare as ts
    except ImportError as exc:
        raise DataSourceError("Tushare SDK is not installed; run: uv add tushare") from exc
    settings = get_settings()
    if not settings.tushare_token:
        raise DataSourceError("Set TUSHARE_TOKEN in .env")
    pro = ts.pro_api(settings.tushare_token)
    if settings.tushare_api_url:
        pro._DataApi__http_url = settings.tushare_api_url.rstrip("/") + "/"
    return ts, pro


def _number(value, *, integer: bool = False):
    if value is None or pd.isna(value):
        return None
    try:
        value = float(value)
        return int(round(value)) if integer else value
    except (TypeError, ValueError):
        return None


def _sum_values(row, *names):
    values = [_number(row.get(name)) for name in names]
    present = [value for value in values if value is not None]
    return int(round(sum(present))) if present else None


def _first_number(row, *names, integer: bool = False):
    for name in names:
        value = _number(row.get(name), integer=integer)
        if value is not None:
            return value
    return None


def _latest_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    result = frame.copy()
    if "report_type" in result:
        standard = result[result["report_type"].astype(str) == "1"]
        if not standard.empty:
            result = standard
    sort_cols = [c for c in ("end_date", "f_ann_date", "ann_date") if c in result]
    if sort_cols:
        result = result.sort_values(sort_cols, ascending=False)
    if "end_date" in result:
        result = result.drop_duplicates("end_date", keep="first")
    return result


def _iso(raw) -> str:
    text = str(raw or "")[:8]
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}" if len(text) == 8 else text


def _date_window(days: int) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=max(days * 2, days + 30))
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


@cached(ttl=86400)
def _stock_universe() -> list[dict]:
    """Return the listed A-share universe used by Web autocomplete."""
    _, pro = _client()
    frame = pro.stock_basic(
        exchange="",
        list_status="L",
        fields="ts_code,symbol,name,industry,market,exchange,cnspell",
    )
    if frame is None or frame.empty:
        return []
    return frame.fillna("").to_dict("records")


def search_securities(query: str, limit: int = 8) -> list[dict]:
    """Search listed A-shares by code, Chinese name, full TS code or pinyin."""
    needle = str(query or "").strip()
    if not needle:
        return []
    upper = needle.upper()
    matches = []
    for row in _stock_universe():
        symbol = str(row.get("symbol") or "")
        ts_code = str(row.get("ts_code") or "").upper()
        name = str(row.get("name") or "")
        spelling = str(row.get("cnspell") or "").upper()
        if not any((upper in symbol.upper(), upper in ts_code, needle in name, upper in spelling)):
            continue
        if upper in {symbol.upper(), ts_code} or needle == name:
            score = 0
        elif symbol.upper().startswith(upper) or ts_code.startswith(upper):
            score = 1
        elif name.startswith(needle):
            score = 2
        elif needle in name:
            score = 3
        elif spelling.startswith(upper):
            score = 4
        else:
            score = 5
        suffix = ts_code.rsplit(".", 1)[-1] if "." in ts_code else ""
        matches.append((score, symbol, {
            "ticker": f"{symbol} CH Equity",
            "symbol": symbol,
            "name": name,
            "exchange": suffix,
            "industry": row.get("industry") or None,
        }))
    matches.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in matches[:max(1, min(int(limit), 20))]]


@cached(ttl=86400)
def get_daily_metrics(ticker: Ticker) -> dict:
    _, pro = _client()
    start, end = _date_window(30)
    frame = pro.daily_basic(ts_code=ticker.tushare_symbol, start_date=start, end_date=end)
    if frame is None or frame.empty:
        return {}
    row = frame.sort_values("trade_date", ascending=False).iloc[0]
    market_cap = _number(row.get("total_mv"), integer=True)
    shares = _number(row.get("total_share"), integer=True)
    shares_float = _number(row.get("float_share"), integer=True)
    dividend_yield = _number(row.get("dv_ttm"))
    return {
        "date": _iso(row.get("trade_date")),
        "pe_ratio": _first_number(row, "pe_ttm", "pe"),
        "pb_ratio": _number(row.get("pb")),
        "ps_ratio": _first_number(row, "ps_ttm", "ps"),
        "dividend_yield": dividend_yield / 100 if dividend_yield is not None else None,
        "market_cap": market_cap * 10_000 if market_cap is not None else None,
        "shares_outstanding": shares * 10_000 if shares is not None else None,
        "shares_float": shares_float * 10_000 if shares_float is not None else None,
    }


@cached(ttl=86400)
def get_profile(ticker: Ticker) -> CompanyProfile:
    _, pro = _client()
    code = ticker.tushare_symbol
    basic = pro.stock_basic(ts_code=code)
    if basic is None or basic.empty:
        raise DataSourceError(f"Tushare returned no profile for {code}")
    row = basic.iloc[0]
    company = {}
    try:
        company_frame = pro.stock_company(ts_code=code)
        if company_frame is not None and not company_frame.empty:
            company = company_frame.iloc[0].to_dict()
    except Exception:
        pass
    metrics = get_daily_metrics(ticker)
    return CompanyProfile(
        symbol=ticker.symbol,
        name=row.get("name"),
        exchange=company.get("exchange") or row.get("exchange") or code.rsplit(".", 1)[-1],
        currency="CNY",
        sector=row.get("industry"),
        industry=row.get("industry"),
        long_description=company.get("introduction") or company.get("main_business"),
        website=company.get("website"),
        address=company.get("office"),
        city=company.get("city"),
        state=company.get("province") or row.get("area"),
        country="China",
        employees=_number(company.get("employees"), integer=True),
        market_cap=metrics.get("market_cap"),
        shares_outstanding=metrics.get("shares_outstanding"),
        shares_float=metrics.get("shares_float"),
        dividend_yield=metrics.get("dividend_yield"),
        issue_type="EQUITY",
    )


@cached(ttl=3600)
def get_price_history(ticker: Ticker, days: int = 365) -> PriceHistory:
    ts, pro = _client()
    start, end = _date_window(days)
    frame = ts.pro_bar(
        api=pro,
        ts_code=ticker.tushare_symbol,
        start_date=start,
        end_date=end,
        adj="qfq",
    )
    if frame is None or frame.empty:
        raise DataSourceError(f"Tushare returned no price history for {ticker.tushare_symbol}")
    frame = frame.sort_values("trade_date").tail(days)
    bars = []
    for _, row in frame.iterrows():
        volume = _number(row.get("vol"))
        amount = _number(row.get("amount"))
        # Tushare volume is in lots (100 shares), amount is in CNY thousands.
        volume_shares = int(round(volume * 100)) if volume is not None else None
        vwap = (amount * 10 / volume) if amount is not None and volume else None
        bars.append(PriceBar(
            date=_iso(row.get("trade_date")),
            open=_number(row.get("open")), high=_number(row.get("high")),
            low=_number(row.get("low")), close=_number(row.get("close")),
            volume=volume_shares, change=_number(row.get("change")),
            change_percent=_number(row.get("pct_chg")), vwap=vwap,
        ))
    return PriceHistory(
        symbol=ticker.symbol, currency="CNY", bars=bars,
        source="Tushare Pro", fetched_at=date.today().isoformat(),
    )


def _income(row, symbol: str, period: str) -> IncomeStatement:
    revenue = _first_number(row, "revenue", "total_revenue", integer=True)
    cost = _number(row.get("oper_cost"), integer=True)
    return IncomeStatement(
        symbol=symbol, date=_iso(row.get("end_date")), fiscal_year=str(row.get("end_date"))[:4],
        period=period, reported_currency="CNY", revenue=revenue,
        cost_of_revenue=cost,
        gross_profit=(revenue - cost if revenue is not None and cost is not None else None),
        operating_expenses=_number(row.get("total_cogs"), integer=True),
        operating_income=_number(row.get("operate_profit"), integer=True),
        ebitda=_number(row.get("ebitda"), integer=True),
        ebit=_first_number(row, "ebit", "operate_profit", integer=True),
        net_income=_first_number(row, "n_income_attr_p", "n_income", integer=True),
        eps=_number(row.get("basic_eps")), eps_diluted=_number(row.get("diluted_eps")),
        rd_expenses=_number(row.get("rd_exp"), integer=True),
        sga_expenses=_sum_values(row, "sell_exp", "admin_exp"),
        income_tax_expense=_number(row.get("income_tax"), integer=True),
        interest_expense=_number(row.get("int_exp"), integer=True),
    )


def _balance(row, symbol: str, period: str) -> BalanceSheet:
    cash = _number(row.get("money_cap"), integer=True)
    short_debt = _sum_values(row, "st_borr", "non_cur_liab_due_1y")
    long_debt = _sum_values(row, "lt_borr", "bond_payable", "lt_payable")
    total_debt = sum(v for v in (short_debt, long_debt) if v is not None)
    if short_debt is None and long_debt is None:
        total_debt = None
    return BalanceSheet(
        symbol=symbol, date=_iso(row.get("end_date")), fiscal_year=str(row.get("end_date"))[:4],
        period=period, reported_currency="CNY", cash_and_equivalents=cash,
        short_term_investments=_number(row.get("trad_asset"), integer=True),
        net_receivables=_number(row.get("accounts_receiv"), integer=True),
        inventory=_number(row.get("inventories"), integer=True),
        total_current_assets=_number(row.get("total_cur_assets"), integer=True),
        total_non_current_assets=_number(row.get("total_nca"), integer=True),
        total_assets=_number(row.get("total_assets"), integer=True),
        accounts_payable=_number(row.get("acct_payable"), integer=True),
        short_term_debt=_number(short_debt, integer=True),
        total_current_liabilities=_number(row.get("total_cur_liab"), integer=True),
        long_term_debt=_number(long_debt, integer=True),
        total_non_current_liabilities=_number(row.get("total_ncl"), integer=True),
        total_liabilities=_number(row.get("total_liab"), integer=True),
        total_stockholders_equity=_number(row.get("total_hldr_eqy_exc_min_int"), integer=True),
        total_equity=_first_number(row, "total_hldr_eqy_inc_min_int", "total_hldr_eqy_exc_min_int", integer=True),
        total_debt=_number(total_debt, integer=True),
        net_debt=_number(total_debt - cash, integer=True) if total_debt is not None and cash is not None else None,
        goodwill=_number(row.get("goodwill"), integer=True),
        retained_earnings=_number(row.get("undistr_porfit"), integer=True),
    )


def _cashflow(row, symbol: str, period: str) -> CashFlow:
    da = _sum_values(row, "depr_fa_coga_dpba", "amort_intang_assets", "lt_amort_deferred_exp")
    wc_cash_effect = _sum_values(row, "decr_inventories", "decr_oper_payable", "incr_oper_payable")
    ocf = _number(row.get("n_cashflow_act"), integer=True)
    capex = _number(row.get("c_pay_acq_const_fiolta"), integer=True)
    return CashFlow(
        symbol=symbol, date=_iso(row.get("end_date")), fiscal_year=str(row.get("end_date"))[:4],
        period=period, reported_currency="CNY",
        net_income=_number(row.get("net_profit"), integer=True),
        depreciation_and_amortization=_number(da, integer=True),
        change_in_working_capital=_number(wc_cash_effect, integer=True),
        operating_cash_flow=ocf, capital_expenditure=capex,
        free_cash_flow=(ocf - capex if ocf is not None and capex is not None else None),
        net_investing_activities=_number(row.get("n_cashflow_inv_act"), integer=True),
        net_financing_activities=_number(row.get("n_cash_flows_fnc_act"), integer=True),
        net_change_in_cash=_number(row.get("n_incr_cash_cash_equ"), integer=True),
    )


@cached(ttl=21600)
def get_financials(ticker: Ticker, years: int = 4) -> Financials:
    _, pro = _client()
    code = ticker.tushare_symbol
    frames = [_latest_rows(call(ts_code=code)) for call in (pro.income, pro.balancesheet, pro.cashflow)]
    annual = [frame[frame["end_date"].astype(str).str.endswith("1231")].head(years) if not frame.empty else frame
              for frame in frames]
    if all(frame.empty for frame in annual):
        raise DataSourceError(f"Tushare returned no annual financials for {code}")
    return Financials(
        symbol=ticker.symbol, currency="CNY",
        income_statements=[_income(row, ticker.symbol, "FY") for _, row in annual[0].iterrows()],
        balance_sheets=[_balance(row, ticker.symbol, "FY") for _, row in annual[1].iterrows()],
        cash_flows=[_cashflow(row, ticker.symbol, "FY") for _, row in annual[2].iterrows()],
    )


_IS_FIELDS = {
    "Total Revenue": "total_revenue", "Cost of Revenue": "oper_cost",
    "R&D Expenses": "rd_exp", "Operating Income": "operate_profit",
    "Pretax Income": "total_profit", "Income Tax Expense": "income_tax",
    "Net Income": "n_income_attr_p", "EPS (Basic)": "basic_eps",
    "EPS (Diluted)": "diluted_eps",
}
_BS_FIELDS = {
    "Cash & Equivalents": "money_cap", "ST Investments": "trad_asset",
    "Accounts Receivable": "accounts_receiv", "Inventory": "inventories",
    "Total Current Assets": "total_cur_assets", "Net PPE": "fix_assets",
    "Goodwill & Intangibles": "goodwill", "Total Assets": "total_assets",
    "Accounts Payable": "acct_payable", "ST Debt": "st_borr",
    "Total Current Liabilities": "total_cur_liab", "Long-Term Debt": "lt_borr",
    "Total Non-Current Liabilities": "total_ncl", "Total Liabilities": "total_liab",
    "Total Stockholders Equity": "total_hldr_eqy_exc_min_int", "Retained Earnings": "undistr_porfit",
}
_CF_FIELDS = {
    "Net Income": "net_profit", "Cash Flow from Operations": "n_cashflow_act",
    "Capital Expenditures": "c_pay_acq_const_fiolta", "Cash Flow from Investing": "n_cashflow_inv_act",
    "Cash Flow from Financing": "n_cash_flows_fnc_act", "Net Change in Cash": "n_incr_cash_cash_equ",
    "Ending Cash": "c_cash_equ_end_period",
}


def _quarter_label(end_date: str) -> str:
    return {"0331": "Q1", "0630": "Q2", "0930": "Q3", "1231": "Q4"}.get(end_date[4:8], "Q?")


def _periods(frame: pd.DataFrame, mapping: dict[str, str], *, cumulative: bool) -> list[QuarterlyPeriod]:
    if frame.empty:
        return []
    rows = frame.sort_values("end_date").to_dict("records")
    previous_by_year: dict[str, dict] = {}
    periods = []
    for row in rows:
        end_date = str(row.get("end_date", ""))
        if end_date[4:8] not in {"0331", "0630", "0930", "1231"}:
            continue
        year = end_date[:4]
        fields = {}
        previous = previous_by_year.get(year)
        for display, source in mapping.items():
            value = _number(row.get(source))
            if cumulative and previous is not None and value is not None:
                prior = _number(previous.get(source))
                if prior is not None:
                    value -= prior
            fields[display] = value
        if mapping is _IS_FIELDS:
            revenue, cost = fields.get("Total Revenue"), fields.get("Cost of Revenue")
            fields["Gross Profit"] = revenue - cost if revenue is not None and cost is not None else None
        if mapping is _CF_FIELDS:
            ocf, capex = fields.get("Cash Flow from Operations"), fields.get("Capital Expenditures")
            fields["Free Cash Flow"] = ocf - capex if ocf is not None and capex is not None else None
        periods.append(QuarterlyPeriod(
            date=_iso(end_date), fiscal_year=year, quarter=_quarter_label(end_date), fields=fields,
        ))
        previous_by_year[year] = row
    return periods


@cached(ttl=21600)
def get_quarterly_financials(ticker: Ticker) -> QuarterlyFinancials:
    _, pro = _client()
    code = ticker.tushare_symbol
    income = _latest_rows(pro.income(ts_code=code))
    balance = _latest_rows(pro.balancesheet(ts_code=code))
    cashflow = _latest_rows(pro.cashflow(ts_code=code))
    if income.empty and balance.empty and cashflow.empty:
        raise DataSourceError(f"Tushare returned no quarterly financials for {code}")
    return QuarterlyFinancials(
        symbol=ticker.symbol, currency="CNY",
        income=_periods(income, _IS_FIELDS, cumulative=True),
        balance=_periods(balance, _BS_FIELDS, cumulative=False),
        cashflow=_periods(cashflow, _CF_FIELDS, cumulative=True),
    )


@cached(ttl=21600)
def get_analyst_ratings(ticker: Ticker) -> AnalystRatings:
    _, pro = _client()
    end = date.today()
    start = end - timedelta(days=365)
    frame = pro.report_rc(
        ts_code=ticker.tushare_symbol,
        start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d"),
    )
    if frame is None or frame.empty:
        return AnalystRatings(symbol=ticker.symbol)
    if "report_date" in frame:
        frame = frame.sort_values("report_date", ascending=False)
    dedupe = [c for c in ("org_name", "report_title") if c in frame]
    if dedupe:
        frame = frame.drop_duplicates(dedupe)
    highs = [_number(v) for v in frame.get("max_price", [])]
    lows = [_number(v) for v in frame.get("min_price", [])]
    highs = [v for v in highs if v is not None and v > 0]
    lows = [v for v in lows if v is not None and v > 0]
    midpoints = [(lo + hi) / 2 for lo, hi in zip(lows, highs)] if len(lows) == len(highs) else highs + lows
    counts = {"strong_buy": 0, "buy": 0, "hold": 0, "sell": 0, "strong_sell": 0}
    for raw in frame.get("rating", []):
        rating = str(raw)
        if "强烈" in rating and ("买" in rating or "推荐" in rating): counts["strong_buy"] += 1
        elif any(word in rating for word in ("买入", "增持", "推荐", "优于")): counts["buy"] += 1
        elif any(word in rating for word in ("卖出", "减持")): counts["sell"] += 1
        else: counts["hold"] += 1
    positive = counts["strong_buy"] + counts["buy"]
    negative = counts["sell"] + counts["strong_sell"]
    consensus = "Buy" if positive > counts["hold"] + negative else "Sell" if negative > positive + counts["hold"] else "Hold"
    return AnalystRatings(
        symbol=ticker.symbol,
        price_target=PriceTarget(
            symbol=ticker.symbol,
            target_high=max(highs) if highs else None,
            target_low=min(lows) if lows else None,
            target_consensus=sum(midpoints) / len(midpoints) if midpoints else None,
            target_median=median(midpoints) if midpoints else None,
        ),
        consensus_rating=consensus,
        num_analysts=int(frame["org_name"].nunique()) if "org_name" in frame else len(frame),
        **counts,
    )


@cached(ttl=86400)
def get_comparables(ticker: Ticker) -> Comparables:
    """Build an A-share peer set from Tushare industry and valuation data."""
    _, pro = _client()
    code = ticker.tushare_symbol
    universe = pd.DataFrame(_stock_universe())
    if universe is None or universe.empty:
        return Comparables(symbol=ticker.symbol, peers=[])
    subject_rows = universe[universe["ts_code"] == code]
    if subject_rows.empty:
        return Comparables(symbol=ticker.symbol, peers=[])
    industry = subject_rows.iloc[0].get("industry")

    subject_metrics = get_daily_metrics(ticker)
    trade_date = str(subject_metrics.get("date") or "").replace("-", "")
    if not trade_date:
        return Comparables(symbol=ticker.symbol, peers=[])
    market = pro.daily_basic(
        trade_date=trade_date,
        fields="ts_code,close,pe_ttm,pb,dv_ttm,total_share,total_mv",
    )
    if market is None or market.empty:
        return Comparables(symbol=ticker.symbol, peers=[])
    candidates = universe[universe["industry"] == industry].merge(market, on="ts_code", how="inner")
    subject_mv = _number(subject_metrics.get("market_cap")) or 0
    if subject_mv > 0:
        candidates["distance"] = candidates["total_mv"].apply(
            lambda value: abs(math.log(max(float(value) * 10_000, 1) / subject_mv))
        )
    else:
        candidates["distance"] = 0.0
    candidates["is_subject"] = candidates["ts_code"] != code
    candidates = candidates.sort_values(["is_subject", "distance"]).head(8)

    peers = []
    for _, row in candidates.iterrows():
        indicator = pd.DataFrame()
        try:
            indicator = _latest_rows(pro.fina_indicator(ts_code=row["ts_code"]))
            annual = indicator[indicator["end_date"].astype(str).str.endswith("1231")] if not indicator.empty else indicator
            if not annual.empty:
                indicator = annual
        except Exception:
            indicator = pd.DataFrame()
        fin = indicator.iloc[0] if not indicator.empty else {}
        market_cap = _number(row.get("total_mv"))
        market_cap = int(round(market_cap * 10_000)) if market_cap is not None else None
        shares = _number(row.get("total_share"))
        shares = shares * 10_000 if shares is not None else None
        revenue_ps = _number(fin.get("total_revenue_ps")) if len(fin) else None
        revenue = int(round(revenue_ps * shares)) if revenue_ps is not None and shares is not None else None
        fcff = _number(fin.get("fcff")) if len(fin) else None
        peers.append(PeerProfile(
            symbol=str(row["ts_code"]), name=row.get("name"), market_cap=market_cap,
            pe_ratio=_number(row.get("pe_ttm")), pb_ratio=_number(row.get("pb")),
            fcf_yield=(fcff / market_cap if fcff is not None and market_cap else None),
            revenue=revenue,
            gross_margin=_number(fin.get("grossprofit_margin")) if len(fin) else None,
            net_margin=_number(fin.get("netprofit_margin")) if len(fin) else None,
            operating_margin=_number(fin.get("op_of_gr")) if len(fin) else None,
            ebitda=_number(fin.get("ebitda"), integer=True) if len(fin) else None,
            total_debt=_number(fin.get("interestdebt"), integer=True) if len(fin) else None,
            dividend_yield=(_number(row.get("dv_ttm")) or 0) / 100,
            currency="CNY",
        ))
    return Comparables(symbol=ticker.symbol, peers=peers)
