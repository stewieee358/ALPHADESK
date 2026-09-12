"""
All terminal formatting lives here. No other layer prints anything.
Uses Rich for panels/tables and plotext for ASCII price charts.
"""

import io
import sys
from datetime import datetime
from typing import Optional

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

# Wrap stdout in UTF-8 so Rich can output full Unicode on Windows (GBK system locale).
# errors='replace' means truly unencodable chars become '?' rather than crashing.
_stdout = io.TextIOWrapper(
    sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
) if hasattr(sys.stdout, "buffer") else sys.stdout

console = Console(file=_stdout, legacy_windows=False)

# ── Bloomberg colour palette ───────────────────────────────────────────────────
ORANGE   = "bright_yellow"
GREEN    = "bright_green"
RED      = "bright_red"
DIM      = "dim white"
HEADER   = "bold bright_white"
SUBHEAD  = "bold yellow"


_CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "HKD": "HK$", "CNY": "¥"}

def _fmt_large(n: Optional[int | float], currency: str = "") -> str:
    """Format large numbers as $3.87T, $391.0B, $97.0M, etc."""
    if n is None:
        return "N/A"
    prefix = _CURRENCY_SYMBOLS.get(currency, f"{currency} " if currency else "")
    abs_n = abs(n)
    sign = "-" if n < 0 else ""
    if abs_n >= 1e12:
        return f"{sign}{prefix}{abs_n / 1e12:.2f}T"
    if abs_n >= 1e9:
        return f"{sign}{prefix}{abs_n / 1e9:.1f}B"
    if abs_n >= 1e6:
        return f"{sign}{prefix}{abs_n / 1e6:.1f}M"
    return f"{sign}{prefix}{abs_n:,.0f}"


def _fmt_pct(n: Optional[float]) -> str:
    if n is None:
        return "N/A"
    return f"{n:.2f}%"


def _kv(label: str, value: str, label_width: int = 22) -> Text:
    t = Text()
    t.append(f"{label:<{label_width}}", style=DIM)
    t.append(value, style=GREEN)
    return t


# ─── DES ──────────────────────────────────────────────────────────────────────

def render_des(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]DES ERROR:[/{RED}] {result['message']}")
        return

    d = result["data"]
    currency = d.get("currency") or "USD"
    mktcap = _fmt_large(d.get("market_cap"), currency)
    div_yield = _fmt_pct(d.get("dividend_yield"))

    # ── Left column ──────────────────────────────────────────────────────────
    left = Table.grid(padding=(0, 1))
    left.add_column(style=DIM, width=22)
    left.add_column(style=GREEN)
    rows_left = [
        ("Name",         d.get("name") or "N/A"),
        ("Exchange",     d.get("exchange") or "N/A"),
        ("Currency",     currency),
        ("Sector",       d.get("sector") or "N/A"),
        ("Industry",     d.get("industry") or "N/A"),
        ("Country",      d.get("country") or "N/A"),
        ("Employees",    f"{d.get('employees'):,}" if d.get("employees") else "N/A"),
    ]
    for label, value in rows_left:
        left.add_row(label, value)

    # ── Right column ─────────────────────────────────────────────────────────
    right = Table.grid(padding=(0, 1))
    right.add_column(style=DIM, width=22)
    right.add_column(style=GREEN)
    rows_right = [
        ("Market Cap",   mktcap),
        ("Shares Out",   _fmt_large(d.get("shares_outstanding"))),
        ("Float",        _fmt_large(d.get("shares_float"))),
        ("Dividend Yld", div_yield),
        ("Beta",         f"{d.get('beta'):.3f}" if d.get("beta") is not None else "N/A"),
        ("Website",      (d.get("website") or "N/A")[:30]),
        ("Phone",        d.get("phone") or "N/A"),
    ]
    for label, value in rows_right:
        right.add_row(label, value)

    # ── Description blurb ────────────────────────────────────────────────────
    desc = (d.get("long_description") or "No description available.")[:300]
    if len(d.get("long_description") or "") > 300:
        desc += "…"

    title = f"[{ORANGE}]DES[/{ORANGE}]  [{HEADER}]{d.get('name', d.get('symbol', ''))}[/{HEADER}]  [{DIM}]{d.get('symbol', '')}[/{DIM}]"

    panel_content = Table.grid(padding=(0, 2))
    panel_content.add_column()
    panel_content.add_column()
    panel_content.add_row(left, right)

    console.print()
    console.print(Panel(panel_content, title=title, border_style="yellow", padding=(1, 2)))
    console.print(Panel(Text(desc, style=DIM), title="Description", border_style="dim", padding=(0, 2)))
    console.print()


# ─── FA ───────────────────────────────────────────────────────────────────────

def render_fa(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]FA ERROR:[/{RED}] {result['message']}")
        return

    d = result["data"]
    currency = d.get("currency") or "USD"
    income = d.get("income_statements", [])
    balance = d.get("balance_sheets", [])
    cashflow = d.get("cash_flows", [])

    if not income:
        console.print(f"[{RED}]FA:[/{RED}] No financial data available.")
        return

    years = [s.get("fiscal_year") or s.get("date", "")[:4] for s in income]
    title = f"[{ORANGE}]FA[/{ORANGE}]  [{HEADER}]{d.get('symbol', '')} — Financial Analysis ({currency})[/{HEADER}]"

    def make_table(section_title: str) -> Table:
        t = Table(title=f"[{SUBHEAD}]{section_title}[/{SUBHEAD}]", border_style="dim",
                  header_style=HEADER, show_lines=False)
        t.add_column("Metric", style=DIM, width=28)
        for y in years:
            t.add_column(str(y), justify="right", style=GREEN)
        return t

    def row(table: Table, label: str, values: list, formatter=None):
        fmt = formatter or (lambda v: _fmt_large(v, currency))
        table.add_row(label, *[fmt(v) if v is not None else "[dim]N/A[/dim]" for v in values])

    # Income statement
    inc_t = make_table("Income Statement")
    row(inc_t, "Revenue",          [s.get("revenue") for s in income])
    row(inc_t, "Gross Profit",     [s.get("gross_profit") for s in income])
    row(inc_t, "Operating Income", [s.get("operating_income") for s in income])
    row(inc_t, "EBITDA",           [s.get("ebitda") for s in income])
    row(inc_t, "Net Income",       [s.get("net_income") for s in income])
    eps_sym = _CURRENCY_SYMBOLS.get(currency, f"{currency} " if currency else "$")
    row(inc_t, "EPS (Diluted)",    [s.get("eps_diluted") for s in income],
        formatter=lambda v: f"{eps_sym}{v:.2f}" if v is not None else "N/A")
    row(inc_t, "R&D",              [s.get("rd_expenses") for s in income])

    # Balance sheet
    if balance:
        bal_t = make_table("Balance Sheet")
        row(bal_t, "Cash & Equivalents", [s.get("cash_and_equivalents") for s in balance])
        row(bal_t, "Total Assets",        [s.get("total_assets") for s in balance])
        row(bal_t, "Total Debt",          [s.get("total_debt") for s in balance])
        row(bal_t, "Net Debt",            [s.get("net_debt") for s in balance])
        row(bal_t, "Total Equity",        [s.get("total_equity") for s in balance])

    # Cash flow
    if cashflow:
        cf_t = make_table("Cash Flow")
        row(cf_t, "Operating Cash Flow", [s.get("operating_cash_flow") for s in cashflow])
        row(cf_t, "CapEx",               [s.get("capital_expenditure") for s in cashflow])
        row(cf_t, "Free Cash Flow",      [s.get("free_cash_flow") for s in cashflow])
        row(cf_t, "Dividends Paid",      [s.get("dividends_paid") for s in cashflow])
        row(cf_t, "Buybacks",            [s.get("common_stock_repurchased") for s in cashflow])

    console.print()
    console.print(Panel(inc_t, title=title, border_style="yellow", padding=(1, 2)))
    if balance:
        console.print(Panel(bal_t, border_style="dim", padding=(1, 2)))
    if cashflow:
        console.print(Panel(cf_t, border_style="dim", padding=(1, 2)))
    console.print()


# ─── GP ───────────────────────────────────────────────────────────────────────

def _sma(values: list[float], window: int) -> list[Optional[float]]:
    """Compute a simple moving average; pads the front with None."""
    result: list[Optional[float]] = []
    for i, _ in enumerate(values):
        if i + 1 < window:
            result.append(None)
        else:
            result.append(sum(values[i + 1 - window : i + 1]) / window)
    return result


def render_gp(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]GP ERROR:[/{RED}] {result['message']}")
        return

    import sys
    import plotext as plt

    # Force UTF-8 on Windows to handle plotext's Unicode drawing characters
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    d       = result["data"]
    bars    = d.get("bars", [])
    symbol  = d.get("symbol", "")
    currency = result.get("currency") or d.get("currency") or ""
    lookback = result.get("lookback", len(bars))

    if not bars:
        console.print(f"[{RED}]GP:[/{RED}] No price data available.")
        return

    bars = bars[-lookback:]

    # ── Extract OHLCV (skip bars with missing close) ───────────────────────────
    valid = [b for b in bars if b.get("close") is not None]
    if not valid:
        console.print(f"[{RED}]GP:[/{RED}] No close prices in data.")
        return

    dates   = [b["date"] for b in valid]
    opens   = [b.get("open")   or b["close"] for b in valid]
    highs   = [b.get("high")   or b["close"] for b in valid]
    lows    = [b.get("low")    or b["close"] for b in valid]
    closes  = [b["close"] for b in valid]
    volumes = [b.get("volume") or 0 for b in valid]

    pct_chg   = ((closes[-1] - closes[0]) / closes[0] * 100) if len(closes) > 1 else 0.0
    chg_color = GREEN if pct_chg >= 0 else RED
    cur_sym   = _CURRENCY_SYMBOLS.get(currency, f"{currency} " if currency else "")

    # ── SMAs (only draw when enough data exists) ───────────────────────────────
    sma50  = _sma(closes, 50)
    sma200 = _sma(closes, 200)
    idx    = list(range(1, len(closes) + 1))

    # ── Candlestick chart (main) ───────────────────────────────────────────────
    plt.clf()
    plt.subplots(2, 1)        # 2 rows, 1 column

    # Row 1 — OHLC candlestick + SMAs
    plt.subplot(1, 1)
    plt.plot_size(110, 22)
    plt.theme("dark")
    plt.title(f"{symbol}  {cur_sym}{closes[-1]:,.2f}  ({pct_chg:+.2f}%  {lookback}d)")
    plt.ylabel("Price")
    plt.candlestick(
        dates,
        {"Open": opens, "Close": closes, "High": highs, "Low": lows},
        colors=["red", "green"],
    )

    # Overlay SMA lines (plotext uses numeric x when mixing with candlestick dates)
    sma50_vals  = [v for v in sma50  if v is not None]
    sma200_vals = [v for v in sma200 if v is not None]
    sma50_idx   = [i for i, v in zip(idx, sma50)  if v is not None]
    sma200_idx  = [i for i, v in zip(idx, sma200) if v is not None]

    if sma50_vals:
        plt.plot(sma50_idx,  sma50_vals,  color="yellow", label="SMA50")
    if sma200_vals:
        plt.plot(sma200_idx, sma200_vals, color="cyan",   label="SMA200")

    # Row 2 — Volume bar chart
    plt.subplot(2, 1)
    plt.plot_size(110, 8)
    plt.theme("dark")
    plt.ylabel("Volume")
    vol_colors = ["green" if c >= o else "red" for c, o in zip(closes, opens)]
    plt.bar(idx, volumes, color=vol_colors, width=0.8)

    plt.show()

    # ── Stats footer ──────────────────────────────────────────────────────────
    period_high = result.get("period_high") or max(highs)
    period_low  = result.get("period_low")  or min(lows)
    avg_vol     = result.get("avg_volume")
    avg_vol_str = f"{avg_vol / 1_000_000:.1f}M" if avg_vol and avg_vol >= 1_000_000 else (
                  f"{avg_vol / 1_000:.0f}K"     if avg_vol else "N/A")

    console.print(
        f"  [{DIM}]Last:[/{DIM}] [{GREEN}]{cur_sym}{closes[-1]:,.2f}[/{GREEN}]   "
        f"[{DIM}]Change:[/{DIM}] [{chg_color}]{pct_chg:+.2f}%[/{chg_color}]   "
        f"[{DIM}]{lookback}d High:[/{DIM}] {cur_sym}{period_high:,.2f}   "
        f"[{DIM}]{lookback}d Low:[/{DIM}] {cur_sym}{period_low:,.2f}   "
        f"[{DIM}]Avg Vol:[/{DIM}] {avg_vol_str}"
    )
    console.print(
        f"  [{DIM}]Period:[/{DIM}] {dates[0]} → {dates[-1]}   "
        f"[{DIM}]Bars:[/{DIM}] {len(valid)}"
    )
    console.print()


# ─── ANR ──────────────────────────────────────────────────────────────────────

def render_anr(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]ANR ERROR:[/{RED}] {result['message']}")
        return

    d = result["data"]
    symbol = d.get("symbol", "")
    pt = d.get("price_target") or {}
    title = f"[{ORANGE}]ANR[/{ORANGE}]  [{HEADER}]{symbol} — Analyst Recommendations[/{HEADER}]"

    t = Table(border_style="dim", header_style=HEADER, show_lines=False)
    t.add_column("Metric", style=DIM, width=24)
    t.add_column("Value", style=GREEN)

    if pt:
        t.add_row("Consensus Target",  f"${pt.get('target_consensus'):.2f}" if pt.get("target_consensus") else "N/A")
        t.add_row("Target High",       f"${pt.get('target_high'):.2f}" if pt.get("target_high") else "N/A")
        t.add_row("Target Low",        f"${pt.get('target_low'):.2f}" if pt.get("target_low") else "N/A")
        t.add_row("Target Median",     f"${pt.get('target_median'):.2f}" if pt.get("target_median") else "N/A")

    if d.get("consensus_rating"):
        t.add_row("Consensus Rating",  str(d.get("consensus_rating")))
    if d.get("num_analysts"):
        t.add_row("# Analysts",        str(d.get("num_analysts")))

    # Buy/hold/sell bar
    buy_ct   = (d.get("strong_buy") or 0) + (d.get("buy") or 0)
    hold_ct  = d.get("hold") or 0
    sell_ct  = (d.get("sell") or 0) + (d.get("strong_sell") or 0)
    if buy_ct or hold_ct or sell_ct:
        t.add_row("", "")
        t.add_row("Strong Buy / Buy",  f"[{GREEN}]{buy_ct}[/{GREEN}]")
        t.add_row("Hold",              f"[yellow]{hold_ct}[/yellow]")
        t.add_row("Sell / Strong Sell",f"[{RED}]{sell_ct}[/{RED}]")

    console.print()
    console.print(Panel(t, title=title, border_style="yellow", padding=(1, 2)))
    console.print()


# ─── COMP ─────────────────────────────────────────────────────────────────────

def render_comp(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]COMP ERROR:[/{RED}] {result['message']}")
        return

    d = result["data"]
    symbol = d.get("symbol", "")
    peers = d.get("peers", [])
    title = f"[{ORANGE}]COMP[/{ORANGE}]  [{HEADER}]{symbol} — Comparables[/{HEADER}]"

    if not peers:
        console.print(f"[{RED}]COMP:[/{RED}] No comparable companies found.")
        return

    t = Table(border_style="dim", header_style=HEADER, show_lines=True, expand=True)
    t.add_column("Ticker",    style=ORANGE, min_width=6,  max_width=8,  no_wrap=True)
    t.add_column("Name",      style=HEADER, min_width=20, max_width=26, no_wrap=True)
    t.add_column("Mkt Cap",   justify="right", style=GREEN, min_width=9)
    t.add_column("Revenue",   justify="right", style=GREEN, min_width=9)
    t.add_column("Gross Mgn", justify="right", style=GREEN, min_width=9)
    t.add_column("Net Mgn",   justify="right", style=GREEN, min_width=8)
    t.add_column("EBITDA",    justify="right", style=GREEN, min_width=9)
    t.add_column("Net Debt",  justify="right", style=GREEN, min_width=9)
    t.add_column("Beta",      justify="right", style=DIM,   min_width=5)

    for p in peers:
        curr = p.get("currency") or ""
        t.add_row(
            p.get("symbol", ""),
            (p.get("name") or "")[:22],
            _fmt_large(p.get("market_cap"), curr),
            _fmt_large(p.get("revenue"), curr),
            _fmt_pct(p.get("gross_margin")),
            _fmt_pct(p.get("net_margin")),
            _fmt_large(p.get("ebitda"), curr),
            _fmt_large(p.get("total_debt"), curr),
            f"{p.get('beta'):.2f}" if p.get("beta") is not None else "N/A",
        )

    console.print()
    console.print(Panel(t, title=title, border_style="yellow", padding=(1, 2)))
    console.print()


# ─── RPT ──────────────────────────────────────────────────────────────────────

def render_rpt(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]RPT ERROR:[/{RED}] {result['message']}")
        return

    d        = result["data"]
    prof     = d.get("profile") or {}
    fin      = d.get("financials") or {}
    val      = d.get("valuation") or {}
    anl      = d.get("analyst") or {}
    rlist    = d.get("ratios_by_year") or []
    currency = fin.get("currency") or prof.get("currency") or ""
    income   = fin.get("income_statements") or []
    sym      = d.get("symbol", "")

    title = f"[{ORANGE}]RPT[/{ORANGE}]  [{HEADER}]{prof.get('name', sym)} — Equity Report[/{HEADER}]"

    # ── Summary grid (left: profile, right: valuation) ────────────────────────
    left = Table.grid(padding=(0, 1))
    left.add_column(style=DIM, width=20)
    left.add_column(style=GREEN)
    for label, val_str in [
        ("Sector",      prof.get("sector") or "N/A"),
        ("Industry",    prof.get("industry") or "N/A"),
        ("Country",     prof.get("country") or "N/A"),
        ("Currency",    currency or "N/A"),
        ("Employees",   f"{prof.get('employees'):,}" if prof.get("employees") else "N/A"),
        ("Beta",        f"{prof.get('beta'):.2f}" if prof.get("beta") is not None else "N/A"),
    ]:
        left.add_row(label, val_str)

    right = Table.grid(padding=(0, 1))
    right.add_column(style=DIM, width=20)
    right.add_column(style=GREEN)
    for label, val_str in [
        ("Mkt Cap",     _fmt_large(val.get("market_cap"), currency)),
        ("Price",       f"{_CURRENCY_SYMBOLS.get(currency, currency+' ')}{val.get('current_price'):.2f}" if val.get("current_price") else "N/A"),
        ("P/E",         f"{val.get('pe_ratio'):.1f}x" if val.get("pe_ratio") else "N/A"),
        ("EV/EBITDA",   f"{val.get('ev_to_ebitda'):.1f}x" if val.get("ev_to_ebitda") else "N/A"),
        ("FCF Yield",   f"{val.get('fcf_yield')*100:.1f}%" if val.get("fcf_yield") else "N/A"),
        ("Div Yield",   _fmt_pct(val.get("dividend_yield"))),
    ]:
        right.add_row(label, val_str)

    grid = Table.grid(padding=(0, 3))
    grid.add_column(); grid.add_column()
    grid.add_row(left, right)

    # ── Latest-year key metrics ────────────────────────────────────────────────
    metrics = Table(border_style="dim", header_style=HEADER, show_lines=False)
    metrics.add_column("Metric", style=DIM, width=22)
    if income:
        latest_yr = income[0].get("fiscal_year") or ""
        metrics.add_column(f"Latest ({latest_yr})", justify="right", style=GREEN)
        for label, key in [
            ("Revenue",          "revenue"),
            ("Gross Profit",     "gross_profit"),
            ("EBITDA",           "ebitda"),
            ("Net Income",       "net_income"),
        ]:
            metrics.add_row(label, _fmt_large(income[0].get(key), currency))

        if rlist:
            r = rlist[0]
            for label, key, fmt in [
                ("Gross Margin",  "gross_margin",  lambda v: _fmt_pct(v)),
                ("Net Margin",    "net_margin",     lambda v: _fmt_pct(v)),
                ("ROE",           "roe",            lambda v: _fmt_pct(v)),
            ]:
                metrics.add_row(label, fmt(r.get(key)))

    # ── Analyst row ───────────────────────────────────────────────────────────
    pt  = anl.get("price_target") or {}
    rating_str = anl.get("consensus_rating") or "N/A"
    target_str = f"{_CURRENCY_SYMBOLS.get(currency, '')}{pt.get('target_consensus'):.2f}" if pt.get("target_consensus") else "N/A"

    console.print()
    console.print(Panel(grid, title=title, border_style="yellow", padding=(1, 2)))
    console.print(Panel(metrics, title=f"[{SUBHEAD}]Key Metrics[/{SUBHEAD}]", border_style="dim", padding=(1, 2)))

    analyst_line = (
        f"  [{DIM}]Consensus:[/{DIM}] [{GREEN}]{rating_str}[/{GREEN}]   "
        f"[{DIM}]Price Target:[/{DIM}] [{GREEN}]{target_str}[/{GREEN}]   "
        f"[{DIM}]# Analysts:[/{DIM}] [{GREEN}]{anl.get('num_analysts') or 'N/A'}[/{GREEN}]"
    )
    console.print(analyst_line)
    console.print()

    # ── Save HTML ─────────────────────────────────────────────────────────────
    try:
        from mini_bloomberg.render.html_renderer import render_report_html
        out_path = render_report_html(result)
        console.print(f"[{DIM}]Full report saved →[/{DIM}] [{GREEN}]{out_path}[/{GREEN}]")
    except Exception as e:
        console.print(f"[{RED}]Could not save HTML report: {e}[/{RED}]")
    console.print()


# ─── RV ───────────────────────────────────────────────────────────────────────

def render_rv(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]RV ERROR:[/{RED}] {result['message']}")
        return

    d        = result["data"]
    sym      = d.get("symbol", "")
    name     = d.get("name") or sym
    currency = d.get("currency") or ""
    val      = d.get("valuation") or {}
    ratios   = d.get("ratios") or {}
    peers    = d.get("peers") or []

    title = f"[{ORANGE}]RV[/{ORANGE}]  [{HEADER}]{name} — Relative Value[/{HEADER}]"

    t = Table(border_style="dim", header_style=HEADER, show_lines=True, expand=True)
    t.add_column("Ticker",    style=ORANGE, min_width=7,  no_wrap=True)
    t.add_column("Name",      style=HEADER, min_width=20, max_width=24, no_wrap=True)
    t.add_column("P/E",       justify="right", style=GREEN, min_width=6)
    t.add_column("EV/EBITDA", justify="right", style=GREEN, min_width=9)
    t.add_column("EV/Sales",  justify="right", style=GREEN, min_width=8)
    t.add_column("P/B",       justify="right", style=GREEN, min_width=6)
    t.add_column("FCF Yld",   justify="right", style=GREEN, min_width=8)
    t.add_column("Net Mgn",   justify="right", style=DIM,   min_width=8)
    t.add_column("Gr Mgn",    justify="right", style=DIM,   min_width=8)

    def _x(v):
        return f"{v:.1f}x" if v is not None else "[dim]N/A[/dim]"
    def _pp(v):
        return f"{v*100:.1f}%" if v is not None else "[dim]N/A[/dim]"

    # Primary ticker row
    t.add_row(
        f"[bold]{sym}[/bold]",
        name[:22],
        _x(val.get("pe_ratio")),
        _x(val.get("ev_to_ebitda")),
        _x(val.get("ev_to_sales")),
        _x(val.get("pb_ratio")),
        _pp(val.get("fcf_yield")),
        _pp(ratios.get("net_margin")),
        _pp(ratios.get("gross_margin")),
    )

    # Peer rows — compute approximate EV/EBITDA and EV/Sales from available data
    for p in peers:
        ev_peer = None
        if p.get("market_cap") is not None and p.get("total_debt") is not None:
            ev_peer = p["market_cap"] + (p["total_debt"] or 0)

        ev_ebitda = None
        if ev_peer and p.get("ebitda") and p["ebitda"] != 0:
            ev_ebitda = ev_peer / p["ebitda"]

        ev_sales = None
        if ev_peer and p.get("revenue") and p["revenue"] != 0:
            ev_sales = ev_peer / p["revenue"]

        gross_mgn = p.get("gross_margin")
        net_mgn   = p.get("net_margin")
        # COMP stores margins as percentages (0-100); convert back to 0-1 for _pp
        gross_mgn = gross_mgn / 100 if gross_mgn is not None else None
        net_mgn   = net_mgn   / 100 if net_mgn   is not None else None

        t.add_row(
            p.get("symbol", ""),
            (p.get("name") or "")[:22],
            _x(p.get("pe_ratio")),
            _x(ev_ebitda),
            _x(ev_sales),
            _x(p.get("pb_ratio")),
            _pp(p.get("fcf_yield")),
            _pp(net_mgn),
            _pp(gross_mgn),
        )

    console.print()
    console.print(Panel(t, title=title, border_style="yellow", padding=(1, 2)))
    console.print()


# ─── Error / status ───────────────────────────────────────────────────────────

def render_error(message: str) -> None:
    console.print(f"[{RED}]ERROR:[/{RED}] {message}")


def render_status(message: str) -> None:
    console.print(f"[{DIM}]{message}[/{DIM}]")


def render_loaded(ticker_str: str) -> None:
    console.print(f"[{ORANGE}]Security loaded:[/{ORANGE}] [{GREEN}]{ticker_str}[/{GREEN}]")


# ─── FX: FXIP ─────────────────────────────────────────────────────────────────

def render_fxip(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]FXIP ERROR:[/{RED}] {result['message']}")
        return

    d     = result["data"]
    group = result.get("group", "g10").upper()
    quote = result.get("quote", "USD")
    rates = d.get("rates", [])
    as_of = d.get("as_of", "")

    title = (
        f"[{ORANGE}]FXIP[/{ORANGE}]  "
        f"[{HEADER}]FX Monitor — {group} vs {quote}[/{HEADER}]  "
        f"[{DIM}]{as_of}[/{DIM}]"
    )

    t = Table(border_style="dim", header_style=HEADER, show_lines=False, expand=True)
    t.add_column("Pair",      style=ORANGE,  min_width=8,  no_wrap=True)
    t.add_column("Spot",      justify="right", style=GREEN,  min_width=12)
    t.add_column("Chg %",     justify="right", min_width=8)
    t.add_column("52W High",  justify="right", style=DIM,    min_width=12)
    t.add_column("52W Low",   justify="right", style=DIM,    min_width=12)

    def _spot(v):
        return f"{v:.4f}" if v is not None else "N/A"

    def _chg(v):
        if v is None:
            return "N/A"
        colour = GREEN if v >= 0 else RED
        arrow  = "▲" if v >= 0 else "▼"
        return f"[{colour}]{arrow} {abs(v):.2f}%[/{colour}]"

    for r in rates:
        t.add_row(
            r.get("pair", ""),
            _spot(r.get("rate")),
            _chg(r.get("change_pct")),
            _spot(r.get("high_52w")),
            _spot(r.get("low_52w")),
        )

    console.print()
    console.print(Panel(t, title=title, border_style="yellow", padding=(1, 2)))
    console.print()


# ─── FX: FXCA ─────────────────────────────────────────────────────────────────

def render_fxca(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]FXCA ERROR:[/{RED}] {result['message']}")
        return

    d = result["data"]
    from_ccy  = d.get("from_currency", "")
    to_ccy    = d.get("to_currency", "")
    amount    = d.get("amount", 0)
    rate      = d.get("rate")
    converted = d.get("converted")
    as_of     = d.get("as_of", "")

    title = (
        f"[{ORANGE}]FXCA[/{ORANGE}]  "
        f"[{HEADER}]FX Calculator — {from_ccy} → {to_ccy}[/{HEADER}]  "
        f"[{DIM}]{as_of}[/{DIM}]"
    )

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style=DIM, min_width=20)
    grid.add_column(style=GREEN)

    rate_str      = f"{rate:.6f}" if rate is not None else "N/A"
    converted_str = f"{converted:,.4f} {to_ccy}" if converted is not None else "N/A"
    amount_str    = f"{amount:,.4f} {from_ccy}"

    grid.add_row("Amount",    amount_str)
    grid.add_row("Spot Rate", f"1 {from_ccy} = {rate_str} {to_ccy}")
    grid.add_row("Converted", converted_str)

    console.print()
    console.print(Panel(grid, title=title, border_style="yellow", padding=(1, 3)))
    console.print()


# ─── FX: FXHV ─────────────────────────────────────────────────────────────────

def render_fxhv(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]FXHV ERROR:[/{RED}] {result['message']}")
        return

    d     = result["data"]
    pair  = d.get("pair", "")
    as_of = d.get("as_of", "")

    title = (
        f"[{ORANGE}]FXHV[/{ORANGE}]  "
        f"[{HEADER}]{pair} — Historical Volatility[/{HEADER}]  "
        f"[{DIM}]{as_of}[/{DIM}]"
    )

    t = Table(border_style="dim", header_style=HEADER, show_lines=False)
    t.add_column("Window",            style=DIM, min_width=8)
    t.add_column("Ann. HV (% p.a.)", justify="right", style=GREEN, min_width=18)

    windows = [
        ("10-Day",  "vol_10d"),
        ("20-Day",  "vol_20d"),
        ("30-Day",  "vol_30d"),
        ("60-Day",  "vol_60d"),
        ("90-Day",  "vol_90d"),
        ("180-Day", "vol_180d"),
        ("1-Year",  "vol_1y"),
    ]

    for label, key in windows:
        val = d.get(key)
        val_str = f"{val:.2f}%" if val is not None else "N/A"
        t.add_row(label, val_str)

    console.print()
    console.print(Panel(t, title=title, border_style="yellow", padding=(1, 2)))
    console.print()


# ─── FX: FRD ──────────────────────────────────────────────────────────────────

def render_frd(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]FRD ERROR:[/{RED}] {result['message']}")
        return

    d     = result["data"]
    pair  = d.get("pair", "")
    spot  = d.get("spot")
    as_of = d.get("as_of", "")
    note  = result.get("note", "")

    spot_str = f"{spot:.5f}" if spot is not None else "N/A"
    title = (
        f"[{ORANGE}]FRD[/{ORANGE}]  "
        f"[{HEADER}]{pair} Forward Rates[/{HEADER}]  "
        f"[{DIM}]Spot: {spot_str}  {as_of}[/{DIM}]"
    )

    t = Table(border_style="dim", header_style=HEADER, show_lines=False, expand=False)
    t.add_column("Tenor",          style=ORANGE, min_width=6,  no_wrap=True)
    t.add_column("Days",           justify="right", style=DIM,  min_width=5)
    t.add_column("Fwd Rate",       justify="right", style=GREEN, min_width=12)
    t.add_column("Fwd Pts (pips)", justify="right", style=GREEN, min_width=15)
    t.add_column("Impl Yld Diff",  justify="right", style=DIM,   min_width=14)

    for tenor in d.get("tenors", []):
        fwd  = tenor.get("forward_rate")
        pts  = tenor.get("forward_points")
        diff = tenor.get("implied_yield_diff")

        fwd_str  = f"{fwd:.5f}" if fwd is not None else "N/A"
        pts_str  = f"{pts:+.2f}" if pts is not None else "N/A"
        diff_str = f"{diff:+.2f}%" if diff is not None else "N/A"

        t.add_row(
            tenor.get("tenor", ""),
            str(tenor.get("days", "")),
            fwd_str,
            pts_str,
            diff_str,
        )

    console.print()
    console.print(Panel(t, title=title, border_style="yellow", padding=(1, 2)))
    if note:
        console.print(f"  [{DIM}]i  {note}[/{DIM}]")
    console.print()


# ─── FX: WCR ──────────────────────────────────────────────────────────────────

def render_wcr(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]WCR ERROR:[/{RED}] {result['message']}")
        return

    d       = result["data"]
    group   = result.get("group", "g10").upper()
    sort_by = result.get("sort_by", "1d").upper()
    as_of   = d.get("as_of", "")

    title = (
        f"[{ORANGE}]WCR[/{ORANGE}]  "
        f"[{HEADER}]World Currency Ranker — {group} vs USD[/{HEADER}]  "
        f"[{DIM}]Sorted by {sort_by}  {as_of}[/{DIM}]"
    )

    t = Table(border_style="dim", header_style=HEADER, show_lines=False, expand=True)
    t.add_column("Rank", justify="right", style=DIM,    min_width=5)
    t.add_column("CCY",  style=ORANGE,    min_width=5,  no_wrap=True)
    t.add_column("Spot", justify="right", style=GREEN,  min_width=10)
    t.add_column("1D",   justify="right", min_width=8)
    t.add_column("1W",   justify="right", min_width=8)
    t.add_column("1M",   justify="right", min_width=8)
    t.add_column("3M",   justify="right", min_width=8)
    t.add_column("YTD",  justify="right", min_width=8)

    def _pct(v):
        if v is None:
            return "N/A"
        colour = GREEN if v >= 0 else RED
        arrow  = "▲" if v >= 0 else "▼"
        return f"[{colour}]{arrow}{abs(v):.2f}%[/{colour}]"

    for rank, row in enumerate(d.get("rows", []), start=1):
        spot = row.get("spot")
        t.add_row(
            str(rank),
            row.get("currency", ""),
            f"{spot:.4f}" if spot is not None else "N/A",
            _pct(row.get("change_1d")),
            _pct(row.get("change_1w")),
            _pct(row.get("change_1m")),
            _pct(row.get("change_3m")),
            _pct(row.get("change_ytd")),
        )

    console.print()
    console.print(Panel(t, title=title, border_style="yellow", padding=(1, 2)))
    console.print()


# ─── NEWS ─────────────────────────────────────────────────────────────────────

def render_news(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]NEWS ERROR:[/{RED}] {result['message']}")
        return

    d = result["data"]
    symbol = d.get("symbol", "")
    articles = d.get("articles", [])

    if not articles:
        console.print(f"[{RED}]NEWS:[/{RED}] No recent headlines found for {symbol}.")
        return

    title = f"[{ORANGE}]NEWS[/{ORANGE}]  [{HEADER}]{symbol} — Recent Headlines[/{HEADER}]  [{DIM}]{len(articles)} stories[/{DIM}]"

    t = Table(border_style="dim", header_style=HEADER, show_lines=True, expand=True)
    t.add_column("#",        justify="right", style=DIM,   width=3)
    t.add_column("Date",     style=ORANGE,    width=12, no_wrap=True)
    t.add_column("Source",   style=GREEN,     max_width=16)
    t.add_column("Headline", style=HEADER,    min_width=28)
    t.add_column("Summary",  style=DIM,       min_width=28)

    for i, a in enumerate(articles, start=1):
        summary = (a.get("text") or "").replace("\n", " ").strip()
        if len(summary) > 160:
            summary = summary[:160] + "…"
        title = a.get("title") or "(untitled)"
        # Terminals can't show a link inline — hyperlink the headline instead
        url = a.get("url") or ""
        headline = f"[link={url}]{title}[/link]" if url.startswith(("http://", "https://")) else title
        t.add_row(
            str(i),
            (a.get("date") or "")[:10] or "N/A",
            a.get("source") or "—",
            headline,
            summary or "—",
        )

    console.print()
    console.print(Panel(t, title=title, border_style="yellow", padding=(1, 2)))
    console.print()


# ─── DCF ──────────────────────────────────────────────────────────────────────

def render_dcf(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]DCF ERROR:[/{RED}] {result['message']}")
        return

    d = result["data"]
    symbol = d.get("symbol", "")
    currency = d.get("currency") or "USD"
    sym_c = _CURRENCY_SYMBOLS.get(currency, f"{currency} " if currency else "$")

    def _rate(v):
        return f"{v * 100:.2f}%" if v is not None else "N/A"

    title = f"[{ORANGE}]DCF[/{ORANGE}]  [{HEADER}]{symbol} — Discounted Cash Flow ({currency})[/{HEADER}]"

    # ── WACC inputs (left) / valuation bridge (right) ─────────────────────────
    left = Table.grid(padding=(0, 1))
    left.add_column(style=DIM, width=22)
    left.add_column(style=GREEN)
    for label, value in [
        ("Risk-free (10Y UST)", _rate(d.get("rf"))),
        ("Equity Risk Premium", _rate(d.get("erp"))),
        ("Country Risk Prem.",  _rate(d.get("crp"))),
        ("Beta (levered)",      f"{d.get('beta_levered'):.3f}" if d.get("beta_levered") is not None else "N/A"),
        ("Cost of Equity",      _rate(d.get("cost_of_equity"))),
        ("Cost of Debt",        _rate(d.get("cost_of_debt"))),
        ("Tax Rate",            _rate(d.get("tax_rate"))),
        ("WACC",                _rate(d.get("wacc"))),
        ("Terminal Growth",     _rate(d.get("terminal_growth"))),
    ]:
        left.add_row(label, value)

    right = Table.grid(padding=(0, 1))
    right.add_column(style=DIM, width=22)
    right.add_column(style=GREEN)
    for label, value in [
        ("PV of Forecast FCFF", _fmt_large(d.get("pv_discrete"), currency)),
        ("Terminal Value",      _fmt_large(d.get("terminal_value"), currency)),
        ("PV of Terminal",      _fmt_large(d.get("pv_terminal"), currency)),
        ("Enterprise Value",    _fmt_large(d.get("enterprise_value_dcf"), currency)),
        ("Less: Total Debt",    _fmt_large(d.get("total_debt"), currency)),
        ("Plus: Cash",          _fmt_large(d.get("cash"), currency)),
        ("Equity Value",        _fmt_large(d.get("equity_value_dcf"), currency)),
        ("Shares Outstanding",  _fmt_large(d.get("shares_outstanding"))),
        ("Revenue CAGR",        _rate(d.get("revenue_cagr"))),
    ]:
        right.add_row(label, value)

    grid = Table.grid(padding=(0, 2))
    grid.add_column()
    grid.add_column()
    grid.add_row(left, right)

    # ── Headline: fair value vs market ────────────────────────────────────────
    fair = d.get("dcf_per_share")
    price = d.get("current_price")
    upside = d.get("upside_pct")
    verdict = Table.grid(padding=(0, 3))
    verdict.add_column(style=DIM, width=22)
    verdict.add_column(style=GREEN)
    verdict.add_row("DCF Fair Value", f"[{HEADER}]{sym_c}{fair:,.2f}[/{HEADER}]" if fair else "N/A")
    verdict.add_row("Current Price", f"{sym_c}{price:,.2f}" if price else "N/A")
    if upside is not None:
        colour = GREEN if upside >= 0 else RED
        arrow = "▲" if upside >= 0 else "▼"
        verdict.add_row("Upside / (Downside)", f"[{colour}]{arrow} {abs(upside) * 100:.1f}%[/{colour}]")

    # ── FCFF projection schedule ──────────────────────────────────────────────
    projections = d.get("fcff_projections") or []
    proj_t = None
    if projections:
        proj_t = Table(title=f"[{SUBHEAD}]FCFF Projection[/{SUBHEAD}]", border_style="dim",
                       header_style=HEADER, show_lines=False)
        proj_t.add_column("Metric", style=DIM, width=20)
        for p in projections:
            proj_t.add_column(str(p.get("year", "")), justify="right", style=GREEN)

        def proj_row(label: str, key: str):
            proj_t.add_row(label, *[_fmt_large(p.get(key), currency) for p in projections])

        proj_row("Revenue", "revenue")
        proj_row("EBIT", "ebit")
        proj_row("EBIT after tax", "ebit_after_tax")
        proj_row("D&A", "da")
        proj_row("Δ NWC", "nwc_change")
        proj_row("CapEx", "capex")
        proj_row("FCFF", "fcff")
        proj_t.add_row(
            "PV factor",
            *[f"{p.get('pv_factor'):.3f}" if p.get("pv_factor") is not None else "N/A" for p in projections],
        )
        proj_row("PV of FCFF", "pv_fcff")

    # ── Sensitivity grid ──────────────────────────────────────────────────────
    s_wacc = d.get("sensitivity_wacc") or []
    s_tg = d.get("sensitivity_tg") or []
    s_grid = d.get("sensitivity_grid") or []
    sens_t = None
    if s_wacc and s_tg and s_grid:
        sens_t = Table(title=f"[{SUBHEAD}]Sensitivity — Fair Value per Share (WACC x g)[/{SUBHEAD}]",
                       border_style="dim", header_style=HEADER, show_lines=False)
        sens_t.add_column("WACC \\ g", style=DIM, width=10)
        for g in s_tg:
            sens_t.add_column(f"{g * 100:.1f}%", justify="right", style=GREEN)
        for w, row in zip(s_wacc, s_grid):
            cells = []
            for v in row:
                if not v:
                    cells.append("[dim]N/A[/dim]")
                elif price and v > price:
                    cells.append(f"[{GREEN}]{sym_c}{v:,.2f}[/{GREEN}]")
                elif price:
                    cells.append(f"[{RED}]{sym_c}{v:,.2f}[/{RED}]")
                else:
                    cells.append(f"{sym_c}{v:,.2f}")
            sens_t.add_row(f"{w * 100:.2f}%", *cells)

    console.print()
    console.print(Panel(verdict, title=title, border_style="yellow", padding=(1, 2)))
    console.print(Panel(grid, title=f"[{SUBHEAD}]WACC & Equity Bridge[/{SUBHEAD}]",
                        border_style="dim", padding=(1, 2)))
    if proj_t:
        console.print(Panel(proj_t, border_style="dim", padding=(1, 2)))
    if sens_t:
        console.print(Panel(sens_t, border_style="dim", padding=(1, 2)))
    if d.get("using_fallback_rates"):
        console.print(f"[{DIM}]Note: live Treasury/Damodaran fetch failed — fallback rates used.[/{DIM}]")
    console.print()


# ─── QTR ──────────────────────────────────────────────────────────────────────

_QTR_SECTIONS = [
    ("income",   "Income Statement"),
    ("balance",  "Balance Sheet"),
    ("cashflow", "Cash Flow"),
]


def render_qtr(result: dict) -> None:
    if result["status"] == "error":
        console.print(f"[{RED}]QTR ERROR:[/{RED}] {result['message']}")
        return

    d = result["data"]
    symbol = d.get("symbol", "")
    currency = d.get("currency") or "USD"

    sections = [(f, t) for f, t in _QTR_SECTIONS if d.get(f)]
    if not sections:
        console.print(f"[{RED}]QTR:[/{RED}] No quarterly data available for {symbol}.")
        return

    title = f"[{ORANGE}]QTR[/{ORANGE}]  [{HEADER}]{symbol} — Quarterly Financials ({currency})[/{HEADER}]"

    tables = []
    for field, section_title in sections:
        periods = d[field]
        t = Table(title=f"[{SUBHEAD}]{section_title}[/{SUBHEAD}]", border_style="dim",
                  header_style=HEADER, show_lines=False)
        t.add_column("Metric", style=DIM, width=28)
        for p in periods:
            t.add_column(f"{p.get('fiscal_year', '')} {p.get('quarter', '')}".strip(),
                         justify="right", style=GREEN)

        # Union of row names across periods, preserving first-seen order.
        # Rows prefixed "~" are company-specific extras from the source filing.
        row_names: list[str] = []
        for p in periods:
            for name in (p.get("fields") or {}):
                if name not in row_names:
                    row_names.append(name)

        cur_sym = _CURRENCY_SYMBOLS.get(currency, f"{currency} " if currency else "$")
        for name in row_names:
            values = [(p.get("fields") or {}).get(name) for p in periods]
            if all(v is None for v in values):
                continue
            label = name[1:] + " *" if name.startswith("~") else name
            # Per-share figures are small — _fmt_large would round them to whole units
            per_share = "EPS" in name.upper() or "PER SHARE" in name.upper()
            cells = [
                "[dim]N/A[/dim]" if v is None
                else (f"{cur_sym}{v:,.2f}" if per_share else _fmt_large(v, currency))
                for v in values
            ]
            t.add_row(label, *cells)

        tables.append(t)

    console.print()
    console.print(Panel(tables[0], title=title, border_style="yellow", padding=(1, 2)))
    for t in tables[1:]:
        console.print(Panel(t, border_style="dim", padding=(1, 2)))
    console.print(f"[{DIM}]* company-specific line item from the source filing[/{DIM}]")
    console.print()
