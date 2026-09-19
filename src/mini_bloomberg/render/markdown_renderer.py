"""
Markdown report renderer for RPT.
Writes a self-contained .md file to reports/{SYMBOL}_{YYYYMMDD}.md in the project root.
Returns the Path of the written file.
"""

from pathlib import Path
from typing import Optional

_REPORTS_DIR = Path(__file__).parent.parent.parent.parent / "reports"

_CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
    "HKD": "HK$", "CNY": "¥", "KRW": "₩", "AUD": "A$",
    "SGD": "S$", "INR": "₹",
}


def _sym(currency: str) -> str:
    return _CURRENCY_SYMBOLS.get(currency, f"{currency} " if currency else "")


def _n(v, currency: str = "") -> str:
    if v is None:
        return "N/A"
    prefix = _sym(currency)
    sign = "-" if v < 0 else ""
    av = abs(v)
    if av >= 1e12:
        return f"{sign}{prefix}{av/1e12:.2f}T"
    if av >= 1e9:
        return f"{sign}{prefix}{av/1e9:.1f}B"
    if av >= 1e6:
        return f"{sign}{prefix}{av/1e6:.1f}M"
    return f"{sign}{prefix}{av:,.0f}"


def _pct(v) -> str:
    """Ratio → percent: 0.469 → '46.9%'. Use for computed ratios (margins, ROE, etc.)."""
    if v is None:
        return "N/A"
    return f"{v*100:.1f}%"


def _pct_raw(v) -> str:
    """Already-percent value → percent string: 0.38 → '0.38%'. Use for yfinance dividend_yield."""
    if v is None:
        return "N/A"
    return f"{v:.2f}%"


def _x(v) -> str:
    if v is None:
        return "N/A"
    return f"{v:.1f}x"


def _p(v, currency: str = "") -> str:
    if v is None:
        return "N/A"
    return f"{_sym(currency)}{v:.2f}"


def render_report_markdown(result: dict) -> Path:
    """Write the full equity report as Markdown and return the file path."""
    if result.get("status") != "ok":
        raise ValueError(result.get("message", "RPT returned error"))

    d     = result["data"]
    sym   = d.get("symbol", "")
    gendt = d.get("generated_at", "")
    prof  = d.get("profile") or {}
    fin   = d.get("financials") or {}
    rlist = d.get("ratios_by_year") or []
    val   = d.get("valuation") or {}
    anl   = d.get("analyst") or {}
    comp  = d.get("comparables") or {}

    currency = fin.get("currency") or prof.get("currency") or ""
    name     = prof.get("name") or sym
    income   = fin.get("income_statements") or []
    balance  = fin.get("balance_sheets") or []
    cashflow = fin.get("cash_flows") or []
    years    = [s.get("fiscal_year") or "" for s in income]

    lines: list[str] = []
    add = lines.append

    # ── Title ──────────────────────────────────────────────────────────────────
    add(f"# {name} ({sym}) — Equity Report")
    add(f"*Generated: {gendt} | Data: FMP, OpenBB/yfinance*")
    add("")
    add("---")
    add("")

    # ── 1. Company Profile ─────────────────────────────────────────────────────
    add("## 1. Company Profile")
    add("")
    add("| Field | Value |")
    add("|---|---|")
    add(f"| Name | {prof.get('name') or 'N/A'} |")
    add(f"| Exchange | {prof.get('exchange') or 'N/A'} |")
    add(f"| Currency | {currency or 'N/A'} |")
    add(f"| Sector | {prof.get('sector') or 'N/A'} |")
    add(f"| Industry | {prof.get('industry') or 'N/A'} |")
    add(f"| Country | {prof.get('country') or 'N/A'} |")
    add(f"| Employees | {prof.get('employees'):,} |" if prof.get('employees') else "| Employees | N/A |")
    add(f"| Website | {prof.get('website') or 'N/A'} |")
    add(f"| Market Cap | {_n(prof.get('market_cap'), currency)} |")
    add(f"| Shares Outstanding | {_n(prof.get('shares_outstanding'))} |")
    add(f"| Float | {_n(prof.get('shares_float'))} |")
    add(f"| Dividend Yield | {_pct_raw(prof.get('dividend_yield'))} |")
    add(f"| Beta | {prof.get('beta'):.3f} |" if prof.get('beta') is not None else "| Beta | N/A |")
    add("")

    if prof.get("long_description"):
        desc = prof["long_description"][:500]
        if len(prof["long_description"]) > 500:
            desc += "…"
        add(f"> {desc}")
        add("")

    add("---")
    add("")

    # ── 2. Financial Summary ───────────────────────────────────────────────────
    add(f"## 2. Financial Summary ({currency})")
    add("")

    if income:
        add("### Income Statement")
        add("")
        hdr = "| Metric | " + " | ".join(years) + " |"
        sep = "|---|" + "---|" * len(years)
        add(hdr); add(sep)
        for label, key in [
            ("Revenue",          "revenue"),
            ("Gross Profit",     "gross_profit"),
            ("Operating Income", "operating_income"),
            ("EBITDA",           "ebitda"),
            ("Net Income",       "net_income"),
            ("EPS (Diluted)",    "eps_diluted"),
        ]:
            if key == "eps_diluted":
                vals = [_p(s.get(key), currency) for s in income]
            else:
                vals = [_n(s.get(key), currency) for s in income]
            add(f"| {label} | " + " | ".join(vals) + " |")
        add("")

    if balance:
        add("### Balance Sheet")
        add("")
        hdr = "| Metric | " + " | ".join([s.get("fiscal_year","") for s in balance]) + " |"
        sep = "|---|" + "---|" * len(balance)
        add(hdr); add(sep)
        for label, key in [
            ("Cash & Equivalents",   "cash_and_equivalents"),
            ("Total Assets",         "total_assets"),
            ("Total Liabilities",    "total_liabilities"),
            ("Total Equity",         "total_equity"),
            ("Total Debt",           "total_debt"),
            ("Net Debt",             "net_debt"),
        ]:
            vals = [_n(s.get(key), currency) for s in balance]
            add(f"| {label} | " + " | ".join(vals) + " |")
        add("")

    if cashflow:
        add("### Cash Flow")
        add("")
        hdr = "| Metric | " + " | ".join([s.get("fiscal_year","") for s in cashflow]) + " |"
        sep = "|---|" + "---|" * len(cashflow)
        add(hdr); add(sep)
        for label, key in [
            ("Operating Cash Flow", "operating_cash_flow"),
            ("CapEx",               "capital_expenditure"),
            ("Free Cash Flow",      "free_cash_flow"),
            ("Dividends Paid",      "dividends_paid"),
        ]:
            vals = [_n(s.get(key), currency) for s in cashflow]
            add(f"| {label} | " + " | ".join(vals) + " |")
        add("")

    add("---")
    add("")

    # ── 3. Financial Ratios ────────────────────────────────────────────────────
    add("## 3. Financial Ratios")
    add("")
    if rlist:
        ryears = [r.get("fiscal_year","") for r in rlist]
        hdr = "| Ratio | " + " | ".join(ryears) + " |"
        sep = "|---|" + "---|" * len(rlist)
        add(hdr); add(sep)
        for label, key, fmt in [
            ("Gross Margin",      "gross_margin",       _pct),
            ("Operating Margin",  "operating_margin",   _pct),
            ("Net Margin",        "net_margin",         _pct),
            ("EBITDA Margin",     "ebitda_margin",      _pct),
            ("ROE",               "roe",                _pct),
            ("ROA",               "roa",                _pct),
            ("Debt / Equity",     "debt_to_equity",     _x),
            ("Net Debt / EBITDA", "net_debt_to_ebitda", _x),
            ("Current Ratio",     "current_ratio",      _x),
            ("Asset Turnover",    "asset_turnover",     _x),
            ("FCF Margin",        "fcf_margin",         _pct),
        ]:
            vals = [fmt(r.get(key)) for r in rlist]
            add(f"| {label} | " + " | ".join(vals) + " |")
    else:
        add("*No ratio data available.*")
    add("")
    add("---")
    add("")

    # ── 4. Valuation Multiples ─────────────────────────────────────────────────
    add("## 4. Valuation Multiples")
    if val.get("price_date"):
        add(f"*As of {val['price_date']}*")
    add("")
    add("| Metric | Value |")
    add("|---|---|")
    add(f"| Current Price | {_p(val.get('current_price'), currency)} |")
    add(f"| Market Cap | {_n(val.get('market_cap'), currency)} |")
    add(f"| Enterprise Value | {_n(val.get('enterprise_value'), currency)} |")
    add(f"| P/E | {_x(val.get('pe_ratio'))} |")
    add(f"| P/B | {_x(val.get('pb_ratio'))} |")
    add(f"| EV/EBITDA | {_x(val.get('ev_to_ebitda'))} |")
    add(f"| EV/Sales | {_x(val.get('ev_to_sales'))} |")
    add(f"| FCF Yield | {_pct(val.get('fcf_yield'))} |")
    add(f"| Dividend Yield | {_pct_raw(val.get('dividend_yield'))} |")
    add("")
    add("---")
    add("")

    # ── 5. Analyst Consensus ───────────────────────────────────────────────────
    add("## 5. Analyst Consensus")
    add("")
    add("| Metric | Value |")
    add("|---|---|")
    pt = anl.get("price_target") or {}
    if pt:
        add(f"| Price Target (Consensus) | {_p(pt.get('target_consensus'), currency)} |")
        add(f"| Price Target High | {_p(pt.get('target_high'), currency)} |")
        add(f"| Price Target Low | {_p(pt.get('target_low'), currency)} |")
        add(f"| Price Target Median | {_p(pt.get('target_median'), currency)} |")
    add(f"| Consensus Rating | {anl.get('consensus_rating') or 'N/A'} |")
    add(f"| # Analysts | {anl.get('num_analysts') or 'N/A'} |")
    buy  = (anl.get("strong_buy") or 0) + (anl.get("buy") or 0)
    hold = anl.get("hold") or 0
    sell = (anl.get("sell") or 0) + (anl.get("strong_sell") or 0)
    if buy or hold or sell:
        add(f"| Buy / Strong Buy | {buy} |")
        add(f"| Hold | {hold} |")
        add(f"| Sell / Strong Sell | {sell} |")
    add("")
    add("*Note: Consensus revenue/EPS estimate stats (mean/high/low) not available from free-tier data.*")
    add("")
    add("---")
    add("")

    # ── 6. Peer Comparison ─────────────────────────────────────────────────────
    add("## 6. Peer Comparison")
    add("")
    peers = comp.get("peers") or []
    if peers:
        add("| Ticker | Name | Mkt Cap | Revenue | Gross Mgn | Net Mgn | EBITDA | EV/EBITDA |")
        add("|---|---|---|---|---|---|---|---|")
        for p in peers:
            pc = p.get("currency") or ""
            ev_peer = None
            if p.get("market_cap") and p.get("total_debt") is not None:
                ev_peer = p["market_cap"] + (p["total_debt"] or 0)
            ev_ebitda = None
            if ev_peer and p.get("ebitda") and p["ebitda"] != 0:
                ev_ebitda = ev_peer / p["ebitda"]
            add(
                f"| {p.get('symbol','')} | {(p.get('name') or '')[:20]} | "
                f"{_n(p.get('market_cap'), pc)} | {_n(p.get('revenue'), pc)} | "
                f"{_pct(p.get('gross_margin')/100 if p.get('gross_margin') is not None else None)} | "
                f"{_pct(p.get('net_margin')/100 if p.get('net_margin') is not None else None)} | "
                f"{_n(p.get('ebitda'), pc)} | {_x(ev_ebitda)} |"
            )
    else:
        add("*No peer data available.*")
    add("")
    add("---")
    add("")

    # ── 7. House View ──────────────────────────────────────────────────────────
    add("## 7. House View (DCF / WACC / SOTP)")
    add("")
    add("*Not available — requires a broker research model.*")
    add("")
    add("---")
    add("")

    # ── 8. Analyst Thesis ──────────────────────────────────────────────────────
    add("## 8. Analyst Thesis")
    add("")
    add("*Not available — requires proprietary broker research.*")
    add("")
    add("---")
    add("")
    add("*Report generated by ALPHADESK v1.0*")

    # ── Write file ─────────────────────────────────────────────────────────────
    _REPORTS_DIR.mkdir(exist_ok=True)
    filename = f"{sym}_{gendt.replace('-', '')}.md"
    out_path = _REPORTS_DIR / filename
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
