"""
Quarterly financial data fetcher.

US tickers  → SEC XBRL via obb.equity.compare.company_facts (free, no key, 5+ years)
Non-US      → yfinance .quarterly_* properties (free, 5-7 quarters)

Returns QuarterlyFinancials with IS / BS / CF broken into QuarterlyPeriod objects.
Each period carries a `fields` dict keyed by display name (same names used by the
XLSX builder in html_renderer.py). Company-specific rows are auto-detected and
prefixed with "~" so the JS layer can visually separate them.
"""

import logging
from datetime import datetime
from typing import Optional

from mini_bloomberg.core.cache import cached
from mini_bloomberg.core.errors import DataSourceError
from mini_bloomberg.core.ticker import Ticker
from mini_bloomberg.data.schemas import QuarterlyFinancials, QuarterlyPeriod

# ─── Universal display-name maps ──────────────────────────────────────────────
# These define the canonical row order in the XLSX.  Keys are source field names;
# values are the display names written into QuarterlyPeriod.fields.

_IS_DISPLAY = [
    "Total Revenue",
    "Cost of Revenue",
    "Gross Profit",
    "R&D Expenses",
    "SG&A Expenses",
    "Total Operating Expenses",
    "Operating Income",
    "EBITDA",
    "Pretax Income",
    "Income Tax Expense",
    "Net Income",
    "EPS (Basic)",
    "EPS (Diluted)",
    "Shares Outstanding (Basic)",
    "Shares Outstanding (Diluted)",
    "D&A",
]

_BS_DISPLAY = [
    "Cash & Equivalents",
    "ST Investments",
    "Cash & ST Investments",
    "Accounts Receivable",
    "Inventory",
    "Total Current Assets",
    "Net PPE",
    "Goodwill & Intangibles",
    "Total Assets",
    "Accounts Payable",
    "ST Debt",
    "Total Current Liabilities",
    "Long-Term Debt",
    "Total Non-Current Liabilities",
    "Total Liabilities",
    "Total Stockholders Equity",
    "Retained Earnings",
    "Total Debt",
    "Net Debt",
]

_CF_DISPLAY = [
    "Net Income",
    "D&A",
    "Stock-Based Compensation",
    "Change in Working Capital",
    "Cash Flow from Operations",
    "Capital Expenditures",
    "Free Cash Flow",
    "Cash Flow from Investing",
    "Dividends Paid",
    "Share Buybacks",
    "Cash Flow from Financing",
    "Net Change in Cash",
    "Ending Cash",
]

# ─── SEC XBRL tag definitions ─────────────────────────────────────────────────
# Each entry: (display_name, [primary_tag, fallback_tag, ...])
# Tags are tried in order; first one that returns ≥1 single-quarter row wins.

_SEC_IS_TAGS = [
    ("Total Revenue",         ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"]),
    ("Cost of Revenue",       ["CostOfRevenue", "CostOfGoodsAndServicesSold"]),
    ("Gross Profit",          ["GrossProfit"]),
    ("R&D Expenses",          ["ResearchAndDevelopmentExpense"]),
    ("SG&A Expenses",         ["SellingGeneralAndAdministrativeExpense", "GeneralAndAdministrativeExpense"]),
    ("Operating Income",      ["OperatingIncomeLoss"]),
    ("Net Income",            ["NetIncomeLoss", "NetIncomeLossAttributableToParent"]),
    ("EPS (Basic)",           ["EarningsPerShareBasic", "IncomeLossFromContinuingOperationsPerBasicShare"]),
    ("EPS (Diluted)",         ["EarningsPerShareDiluted", "IncomeLossFromContinuingOperationsPerDilutedShare"]),
    ("D&A",                   ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization"]),
    ("Income Tax Expense",    ["IncomeTaxExpenseBenefit"]),
]

_SEC_BS_TAGS = [
    ("Cash & Equivalents",          ["CashAndCashEquivalentsAtCarryingValue", "Cash"]),
    ("ST Investments",              ["ShortTermInvestments", "MarketableSecuritiesCurrent"]),
    ("Cash & ST Investments",       ["CashCashEquivalentsAndShortTermInvestments"]),
    ("Accounts Receivable",         ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"]),
    ("Inventory",                   ["InventoryNet"]),
    ("Total Current Assets",        ["AssetsCurrent"]),
    ("Net PPE",                     ["PropertyPlantAndEquipmentNet"]),
    ("Goodwill & Intangibles",      ["Goodwill"]),
    ("Total Assets",                ["Assets"]),
    ("Accounts Payable",            ["AccountsPayableCurrent"]),
    ("ST Debt",                     ["ShortTermBorrowings", "DebtCurrent"]),
    ("Total Current Liabilities",   ["LiabilitiesCurrent"]),
    ("Long-Term Debt",              ["LongTermDebtNoncurrent", "LongTermDebt"]),
    ("Total Liabilities",           ["Liabilities"]),
    ("Total Stockholders Equity",   ["StockholdersEquity"]),
    ("Retained Earnings",           ["RetainedEarningsAccumulatedDeficit"]),
]

_SEC_CF_TAGS = [
    ("Cash Flow from Operations",   ["NetCashProvidedByUsedInOperatingActivities"]),
    ("Capital Expenditures",        ["PaymentsToAcquirePropertyPlantAndEquipment"]),
    ("Cash Flow from Investing",    ["NetCashProvidedByUsedInInvestingActivities"]),
    ("Dividends Paid",              ["PaymentsOfDividends", "DividendsCash"]),
    ("Share Buybacks",              ["PaymentsForRepurchaseOfCommonStock", "StockRepurchasedAndRetiredDuringPeriodValue"]),
    ("Cash Flow from Financing",    ["NetCashProvidedByUsedInFinancingActivities"]),
    ("Stock-Based Compensation",    ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"]),
    ("D&A",                         ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization"]),
    ("Net Income",                  ["NetIncomeLoss"]),
]

# ─── yfinance field maps ───────────────────────────────────────────────────────
# Key = yfinance DataFrame index label → value = display name

_YF_IS_MAP = {
    "Total Revenue":                      "Total Revenue",
    "Cost Of Revenue":                    "Cost of Revenue",
    "Gross Profit":                       "Gross Profit",
    "Research And Development":           "R&D Expenses",
    "Selling General And Administration": "SG&A Expenses",
    "Operating Expense":                  "Total Operating Expenses",
    "Operating Income":                   "Operating Income",
    "EBITDA":                             "EBITDA",
    "Pretax Income":                      "Pretax Income",
    "Tax Provision":                      "Income Tax Expense",
    "Net Income":                         "Net Income",
    "Basic EPS":                          "EPS (Basic)",
    "Diluted EPS":                        "EPS (Diluted)",
    "Basic Average Shares":               "Shares Outstanding (Basic)",
    "Diluted Average Shares":             "Shares Outstanding (Diluted)",
    "Reconciled Depreciation":            "D&A",
    "Normalized EBITDA":                  "EBITDA",
}

_YF_BS_MAP = {
    "Cash And Cash Equivalents":          "Cash & Equivalents",
    "Other Short Term Investments":       "ST Investments",
    "Cash Cash Equivalents And Short Term Investments": "Cash & ST Investments",
    "Accounts Receivable":                "Accounts Receivable",
    "Inventory":                          "Inventory",
    "Current Assets":                     "Total Current Assets",
    "Net PPE":                            "Net PPE",
    "Goodwill And Other Intangible Assets": "Goodwill & Intangibles",
    "Total Assets":                       "Total Assets",
    "Accounts Payable":                   "Accounts Payable",
    "Current Debt":                       "ST Debt",
    "Current Liabilities":                "Total Current Liabilities",
    "Long Term Debt":                     "Long-Term Debt",
    "Total Non Current Liabilities Net Minority Interest": "Total Non-Current Liabilities",
    "Total Liabilities Net Minority Interest": "Total Liabilities",
    "Stockholders Equity":                "Total Stockholders Equity",
    "Retained Earnings":                  "Retained Earnings",
    "Total Debt":                         "Total Debt",
    "Net Debt":                           "Net Debt",
}

_YF_CF_MAP = {
    "Net Income From Continuing Operations": "Net Income",
    "Depreciation And Amortization":         "D&A",
    "Stock Based Compensation":              "Stock-Based Compensation",
    "Change In Working Capital":             "Change in Working Capital",
    "Operating Cash Flow":                   "Cash Flow from Operations",
    "Purchase Of PPE":                       "Capital Expenditures",
    "Free Cash Flow":                        "Free Cash Flow",
    "Investing Cash Flow":                   "Cash Flow from Investing",
    "Cash Dividends Paid":                   "Dividends Paid",
    "Repurchase Of Capital Stock":           "Share Buybacks",
    "Financing Cash Flow":                   "Cash Flow from Financing",
    "Changes In Cash":                       "Net Change in Cash",
    "End Cash Position":                     "Ending Cash",
}

_ALL_DISPLAY = set(_IS_DISPLAY + _BS_DISPLAY + _CF_DISPLAY)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        return None if (f != f) else f  # reject NaN
    except (TypeError, ValueError):
        return None


def _quarter_label(month: int, fiscal_year_end_month: int = 12) -> str:
    """Map a period-end month to Q1/Q2/Q3/Q4 relative to the fiscal year-end.
    Uses ±1 month tolerance to handle 52/53-week fiscal calendars where
    quarter-end dates can slip into an adjacent month (e.g. Apple Q3 ending July 1).
    """
    offset = (month - fiscal_year_end_month) % 12
    # Exact: 0=Q4, 9=Q3, 6=Q2, 3=Q1; with ±1 tolerance for 52-week calendars
    if offset in (11, 0, 1):  return "Q4"
    if offset in (2,  3, 4):  return "Q1"
    if offset in (5,  6, 7):  return "Q2"
    if offset in (8,  9, 10): return "Q3"
    return "Q?"


def _periods_to_quarterly(
    periods: list[QuarterlyPeriod],
    years: int = 4,
) -> list[QuarterlyPeriod]:
    """Keep only the most recent `years` fiscal years, deduplicate by (fy, quarter)."""
    seen: dict[tuple, QuarterlyPeriod] = {}
    for p in periods:
        key = (p.fiscal_year, p.quarter)
        if key not in seen:
            seen[key] = p
    # Sort newest first, limit to `years` distinct fiscal years
    all_fys = sorted({k[0] for k in seen}, reverse=True)[:years]
    result = [v for k, v in seen.items() if k[0] in all_fys]
    return sorted(result, key=lambda p: (p.fiscal_year, p.quarter))


# ─── SEC path ─────────────────────────────────────────────────────────────────

def _fetch_sec_fact(obb, symbol: str, tags: list[str], is_instant: bool = False) -> dict[str, float]:
    """
    Try each XBRL tag in order; return {period_ending_str: value}.
    is_instant=True for balance sheet (point-in-time, no period_beginning).
    is_instant=False for IS (duration facts, filtered to 75-100 day windows).

    A tag is accepted only if it contains at least one entry from the past 3 years
    (guards against companies that switched XBRL tags mid-history, e.g. NVDA).
    If no tag has recent data, falls back to the tag with the most entries overall.
    """
    from datetime import date as _date
    _recent_cutoff = str(_date.today().year - 3)  # e.g. "2023"
    fallback: dict[str, float] = {}

    for tag in tags:
        try:
            r = obb.equity.compare.company_facts(symbol=symbol, fact=tag, provider="sec")
            result: dict[str, float] = {}
            for x in r.results:
                pe = x.period_ending
                if pe is None:
                    continue
                pe_dt = pe if hasattr(pe, "year") else datetime.strptime(str(pe)[:10], "%Y-%m-%d").date()

                if is_instant:
                    key = str(pe_dt)
                    if key not in result:
                        result[key] = float(x.value)
                else:
                    pb = x.period_beginning
                    if pb is None:
                        continue
                    pb_dt = pb if hasattr(pb, "year") else datetime.strptime(str(pb)[:10], "%Y-%m-%d").date()
                    days = abs((pe_dt - pb_dt).days)
                    if 75 <= days <= 100:
                        key = str(pe_dt)
                        if key not in result:
                            result[key] = float(x.value)

            if result:
                # Prefer a tag that has recent data; stash older-only results as fallback
                if any(k >= _recent_cutoff for k in result):
                    return result
                if len(result) > len(fallback):
                    fallback = result
        except Exception:
            continue
    return fallback


def _fetch_sec_cf_standalone(obb, symbol: str, tags: list[str]) -> dict[str, float]:
    """
    Fetch cash flow facts and derive standalone quarterly values from YTD cumulative.
    SEC 10-Qs file CF as YTD (Q2=Q1+Q2, Q3=Q1+Q2+Q3); 10-K has the annual total.
    Derives Q1/Q2/Q3/Q4 standalone by differencing consecutive YTD entries
    that share the same fiscal-year period_beginning.
    """
    for tag in tags:
        try:
            r = obb.equity.compare.company_facts(symbol=symbol, fact=tag, provider="sec")

            # Collect all duration entries grouped by period_beginning
            by_pb: dict[str, list] = {}
            for x in r.results:
                pb, pe = x.period_beginning, x.period_ending
                if pb is None or pe is None:
                    continue
                pb_dt = pb if hasattr(pb, "year") else datetime.strptime(str(pb)[:10], "%Y-%m-%d").date()
                pe_dt = pe if hasattr(pe, "year") else datetime.strptime(str(pe)[:10], "%Y-%m-%d").date()
                days = (pe_dt - pb_dt).days
                if days < 60:  # skip oddities (corrections / very short periods)
                    continue
                pb_str = str(pb_dt)
                pe_str = str(pe_dt)
                # Dedup per (pb, pe): keep first
                group = by_pb.setdefault(pb_str, {})
                if pe_str not in group:
                    group[pe_str] = (days, float(x.value))

            if not by_pb:
                continue

            result: dict[str, float] = {}

            for pb_str, pe_map in by_pb.items():
                # Sort entries by duration
                entries = sorted(pe_map.items(), key=lambda kv: kv[1][0])  # sort by days

                # Only retain plausible quarterly checkpoints: ~Q1(91), ~Q2(182), ~Q3(274), ~Annual(365)
                # Use windows: 60-130, 155-220, 240-310, 330-400
                windows = [(60, 130), (155, 220), (240, 310), (330, 400)]
                checkpoints: list[tuple[str, int, float]] = []  # (pe_str, days, cumulative_val)
                for (lo, hi) in windows:
                    match = [(pe_str, d, v) for pe_str, (d, v) in entries if lo <= d <= hi]
                    if match:
                        checkpoints.append(match[-1])  # take most recent filing for this window

                # Derive standalone from cumulative diff
                prev_cum = 0.0
                for pe_str, days, cum_val in checkpoints:
                    standalone = cum_val - prev_cum
                    if pe_str not in result:
                        result[pe_str] = standalone
                    prev_cum = cum_val

            if result:
                return result
        except Exception:
            continue
    return {}


def _fiscal_year_str(dt, fy_end_month: int) -> str:
    """Return the fiscal year label for a period-end date.
    For companies with non-December FY end, periods after the FY-end month
    belong to the following fiscal year (e.g. Apple Dec 2023 → FY2024).
    """
    if dt.month > fy_end_month:
        return str(dt.year + 1)
    return str(dt.year)


def _detect_fy_end_month(symbol: str) -> int:
    """Detect fiscal year-end month from yfinance annual income statement."""
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        annual = t.income_stmt
        if not annual.empty and len(annual.columns) > 0:
            col = annual.columns[0]
            dt = col if hasattr(col, "month") else datetime.strptime(str(col)[:10], "%Y-%m-%d")
            return dt.month
    except Exception:
        pass
    return 12


def _from_sec(ticker: Ticker) -> QuarterlyFinancials:
    from openbb import obb as _obb

    sym = ticker.symbol
    fy_end_month = _detect_fy_end_month(sym)

    # Collect raw {date_str: value} per display name for each statement
    is_raw: dict[str, dict[str, float]] = {}
    bs_raw: dict[str, dict[str, float]] = {}
    cf_raw: dict[str, dict[str, float]] = {}

    for display, tags in _SEC_IS_TAGS:
        d = _fetch_sec_fact(_obb, sym, tags, is_instant=False)
        if d:
            is_raw[display] = d

    for display, tags in _SEC_BS_TAGS:
        d = _fetch_sec_fact(_obb, sym, tags, is_instant=True)
        if d:
            bs_raw[display] = d

    for display, tags in _SEC_CF_TAGS:
        d = _fetch_sec_cf_standalone(_obb, sym, tags)
        if d:
            cf_raw[display] = d

    if not is_raw and not bs_raw and not cf_raw:
        raise DataSourceError(f"SEC returned no quarterly data for {sym}")

    # Gather all unique period-end dates across all fetched facts
    all_is_dates  = sorted({d for v in is_raw.values()  for d in v}, reverse=True)
    all_bs_dates  = sorted({d for v in bs_raw.values()  for d in v}, reverse=True)
    all_cf_dates  = sorted({d for v in cf_raw.values()  for d in v}, reverse=True)

    def _dates_to_periods(dates, raw, display_list):
        periods = []
        for date_str in dates:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            fy_str = _fiscal_year_str(dt, fy_end_month)
            q = _quarter_label(dt.month, fy_end_month)
            fields: dict[str, Optional[float]] = {}
            for name in display_list:
                v = raw.get(name, {}).get(date_str)
                fields[name] = _safe_float(v)
            periods.append(QuarterlyPeriod(
                date=date_str, fiscal_year=fy_str, quarter=q, fields=fields
            ))
        return _periods_to_quarterly(periods, years=5)

    return QuarterlyFinancials(
        symbol=sym,
        income=_dates_to_periods(all_is_dates, is_raw, _IS_DISPLAY),
        balance=_dates_to_periods(all_bs_dates, bs_raw, _BS_DISPLAY),
        cashflow=_dates_to_periods(all_cf_dates, cf_raw, _CF_DISPLAY),
    )


# ─── yfinance path ────────────────────────────────────────────────────────────

def _df_to_periods(
    df,
    yf_map: dict[str, str],
    display_list: list[str],
    fy_end_month: int = 12,
    years: int = 4,
    anchor_field: Optional[str] = None,
) -> list[QuarterlyPeriod]:
    """Convert a yfinance quarterly DataFrame to QuarterlyPeriod list.

    anchor_field: if set, periods where this display name resolves to None are
    dropped.  This filters phantom column dates that yfinance emits for
    semi-annual reporters (e.g. Lenovo Dec/Jun columns that have almost no data).
    """
    if df is None or df.empty:
        return []

    # Build reverse map: display_name -> set of yf keys that map to it
    # (multiple yf keys can map to same display name; last non-null wins)
    display_to_yf: dict[str, list[str]] = {}
    for yf_key, disp in yf_map.items():
        display_to_yf.setdefault(disp, []).append(yf_key)

    # Company-specific rows: yf rows not in any map
    all_yf_mapped = set(yf_map.keys())
    extra_yf_rows = [r for r in df.index if r not in all_yf_mapped]

    periods = []
    for col in df.columns:
        try:
            dt = col if hasattr(col, "month") else datetime.strptime(str(col)[:10], "%Y-%m-%d")
            date_str = str(dt)[:10]
            fy_str = _fiscal_year_str(dt, fy_end_month)
            q = _quarter_label(dt.month, fy_end_month)
        except Exception:
            continue

        fields: dict[str, Optional[float]] = {}

        # Universal rows
        for disp in display_list:
            val = None
            for yf_key in display_to_yf.get(disp, []):
                if yf_key in df.index:
                    raw = df.at[yf_key, col] if col in df.columns else None
                    v = _safe_float(raw)
                    if v is not None:
                        val = v
                        break
            fields[disp] = val

        # Skip phantom periods: semi-annual reporters emit column dates with no data
        if anchor_field is not None and fields.get(anchor_field) is None:
            continue

        # Company-specific rows (prefixed "~")
        for yf_key in extra_yf_rows:
            try:
                raw = df.at[yf_key, col]
                v = _safe_float(raw)
                if v is not None:
                    fields[f"~{yf_key}"] = v
            except Exception:
                pass

        periods.append(QuarterlyPeriod(
            date=date_str, fiscal_year=fy_str, quarter=q, fields=fields
        ))

    return _periods_to_quarterly(periods, years=years)


def _from_yfinance(ticker: Ticker) -> QuarterlyFinancials:
    import yfinance as yf
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)

    sym = ticker.yfinance_symbol
    t = yf.Ticker(sym)

    qi = t.quarterly_income_stmt
    qb = t.quarterly_balance_sheet
    qc = t.quarterly_cashflow

    # Estimate fiscal year-end month from annual income statement column dates
    fy_end_month = 12
    try:
        annual = t.income_stmt
        if not annual.empty and len(annual.columns) > 0:
            latest_col = annual.columns[0]
            dt = latest_col if hasattr(latest_col, "month") else datetime.strptime(str(latest_col)[:10], "%Y-%m-%d")
            fy_end_month = dt.month
    except Exception:
        pass

    if (qi is None or qi.empty) and (qb is None or qb.empty) and (qc is None or qc.empty):
        raise DataSourceError(f"yfinance returned no quarterly data for {sym}")

    return QuarterlyFinancials(
        symbol=ticker.symbol,
        income=_df_to_periods(qi, _YF_IS_MAP, _IS_DISPLAY, fy_end_month, anchor_field="Total Revenue"),
        balance=_df_to_periods(qb, _YF_BS_MAP, _BS_DISPLAY, fy_end_month, anchor_field="Total Assets"),
        cashflow=_df_to_periods(qc, _YF_CF_MAP, _CF_DISPLAY, fy_end_month, anchor_field="Cash Flow from Operations"),
    )


# ─── Public API ───────────────────────────────────────────────────────────────

@cached(ttl=21600)  # 6h — quarterly filings are infrequent
def get_quarterly_financials(ticker: Ticker) -> QuarterlyFinancials:
    if ticker.is_china:
        from mini_bloomberg.data.providers import tushare_provider
        return tushare_provider.get_quarterly_financials(ticker)
    if ticker.is_us:
        try:
            return _from_sec(ticker)
        except Exception as e:
            raise DataSourceError(f"SEC quarterly fetch failed for {ticker}: {e}") from e
    try:
        return _from_yfinance(ticker)
    except Exception as e:
        raise DataSourceError(f"yfinance quarterly fetch failed for {ticker}: {e}") from e
