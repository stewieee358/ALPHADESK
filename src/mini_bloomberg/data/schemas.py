"""
Pydantic models for all data returned by providers.
Field sets are derived from the Milestone 1 probe output.
All fields are Optional to handle partial data across providers.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, field_validator


# ─── DES ──────────────────────────────────────────────────────────────────────

class CompanyProfile(BaseModel):
    """Source: OpenBB/yfinance equity.profile (primary for all tickers)."""
    symbol: str
    name: Optional[str] = None
    exchange: Optional[str] = None          # e.g. "NMS", "NYQ"
    currency: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    long_description: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    employees: Optional[int] = None
    market_cap: Optional[int] = None
    shares_outstanding: Optional[int] = None
    shares_float: Optional[int] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    issue_type: Optional[str] = None        # "EQUITY"


# ─── FA ───────────────────────────────────────────────────────────────────────

class IncomeStatement(BaseModel):
    """Source: FMP /stable/income-statement (39 fields)."""
    symbol: str
    date: Optional[str] = None
    fiscal_year: Optional[str] = None
    period: Optional[str] = None            # "FY", "Q1", etc.
    reported_currency: Optional[str] = None
    revenue: Optional[int] = None
    cost_of_revenue: Optional[int] = None
    gross_profit: Optional[int] = None
    operating_expenses: Optional[int] = None
    operating_income: Optional[int] = None
    ebitda: Optional[int] = None
    ebit: Optional[int] = None
    net_income: Optional[int] = None
    eps: Optional[float] = None
    eps_diluted: Optional[float] = None
    rd_expenses: Optional[int] = None
    sga_expenses: Optional[int] = None
    income_tax_expense: Optional[int] = None
    interest_expense: Optional[int] = None
    depreciation_and_amortization: Optional[int] = None
    weighted_avg_shares: Optional[int] = None
    weighted_avg_shares_diluted: Optional[int] = None

    @classmethod
    def from_fmp(cls, raw: dict) -> "IncomeStatement":
        return cls(
            symbol=raw.get("symbol", ""),
            date=raw.get("date"),
            fiscal_year=raw.get("fiscalYear"),
            period=raw.get("period"),
            reported_currency=raw.get("reportedCurrency"),
            revenue=raw.get("revenue"),
            cost_of_revenue=raw.get("costOfRevenue"),
            gross_profit=raw.get("grossProfit"),
            operating_expenses=raw.get("operatingExpenses"),
            operating_income=raw.get("operatingIncome"),
            ebitda=raw.get("ebitda"),
            ebit=raw.get("ebit"),
            net_income=raw.get("netIncome"),
            eps=raw.get("eps"),
            eps_diluted=raw.get("epsDiluted"),
            rd_expenses=raw.get("researchAndDevelopmentExpenses"),
            sga_expenses=raw.get("sellingGeneralAndAdministrativeExpenses"),
            income_tax_expense=raw.get("incomeTaxExpense"),
            interest_expense=raw.get("interestExpense"),
            depreciation_and_amortization=raw.get("depreciationAndAmortization"),
            weighted_avg_shares=raw.get("weightedAverageShsOut"),
            weighted_avg_shares_diluted=raw.get("weightedAverageShsOutDil"),
        )


class BalanceSheet(BaseModel):
    """Source: FMP /stable/balance-sheet-statement (61 fields)."""
    symbol: str
    date: Optional[str] = None
    fiscal_year: Optional[str] = None
    period: Optional[str] = None
    reported_currency: Optional[str] = None
    cash_and_equivalents: Optional[int] = None
    short_term_investments: Optional[int] = None
    net_receivables: Optional[int] = None
    inventory: Optional[int] = None
    total_current_assets: Optional[int] = None
    total_non_current_assets: Optional[int] = None
    total_assets: Optional[int] = None
    accounts_payable: Optional[int] = None
    short_term_debt: Optional[int] = None
    total_current_liabilities: Optional[int] = None
    long_term_debt: Optional[int] = None
    total_non_current_liabilities: Optional[int] = None
    total_liabilities: Optional[int] = None
    total_stockholders_equity: Optional[int] = None
    total_equity: Optional[int] = None
    total_debt: Optional[int] = None
    net_debt: Optional[int] = None
    goodwill: Optional[int] = None
    retained_earnings: Optional[int] = None

    @classmethod
    def from_fmp(cls, raw: dict) -> "BalanceSheet":
        return cls(
            symbol=raw.get("symbol", ""),
            date=raw.get("date"),
            fiscal_year=raw.get("fiscalYear"),
            period=raw.get("period"),
            reported_currency=raw.get("reportedCurrency"),
            cash_and_equivalents=raw.get("cashAndCashEquivalents"),
            short_term_investments=raw.get("shortTermInvestments"),
            net_receivables=raw.get("netReceivables"),
            inventory=raw.get("inventory"),
            total_current_assets=raw.get("totalCurrentAssets"),
            total_non_current_assets=raw.get("totalNonCurrentAssets"),
            total_assets=raw.get("totalAssets"),
            accounts_payable=raw.get("accountPayables"),
            short_term_debt=raw.get("shortTermDebt"),
            total_current_liabilities=raw.get("totalCurrentLiabilities"),
            long_term_debt=raw.get("longTermDebt"),
            total_non_current_liabilities=raw.get("totalNonCurrentLiabilities"),
            total_liabilities=raw.get("totalLiabilities"),
            total_stockholders_equity=raw.get("totalStockholdersEquity"),
            total_equity=raw.get("totalEquity"),
            total_debt=raw.get("totalDebt"),
            net_debt=raw.get("netDebt"),
            goodwill=raw.get("goodwill"),
            retained_earnings=raw.get("retainedEarnings"),
        )


class CashFlow(BaseModel):
    """Source: FMP /stable/cash-flow-statement (47 fields)."""
    symbol: str
    date: Optional[str] = None
    fiscal_year: Optional[str] = None
    period: Optional[str] = None
    reported_currency: Optional[str] = None
    net_income: Optional[int] = None
    depreciation_and_amortization: Optional[int] = None
    stock_based_compensation: Optional[int] = None
    change_in_working_capital: Optional[int] = None
    operating_cash_flow: Optional[int] = None
    capital_expenditure: Optional[int] = None
    free_cash_flow: Optional[int] = None
    net_investing_activities: Optional[int] = None
    net_financing_activities: Optional[int] = None
    net_change_in_cash: Optional[int] = None
    dividends_paid: Optional[int] = None
    common_stock_repurchased: Optional[int] = None

    @classmethod
    def from_fmp(cls, raw: dict) -> "CashFlow":
        return cls(
            symbol=raw.get("symbol", ""),
            date=raw.get("date"),
            fiscal_year=raw.get("fiscalYear"),
            period=raw.get("period"),
            reported_currency=raw.get("reportedCurrency"),
            net_income=raw.get("netIncome"),
            depreciation_and_amortization=raw.get("depreciationAndAmortization"),
            stock_based_compensation=raw.get("stockBasedCompensation"),
            change_in_working_capital=raw.get("changeInWorkingCapital"),
            operating_cash_flow=raw.get("operatingCashFlow"),
            capital_expenditure=raw.get("capitalExpenditure"),
            free_cash_flow=raw.get("freeCashFlow"),
            net_investing_activities=raw.get("netCashProvidedByInvestingActivities"),
            net_financing_activities=raw.get("netCashProvidedByFinancingActivities"),
            net_change_in_cash=raw.get("netChangeInCash"),
            dividends_paid=raw.get("commonDividendsPaid"),
            common_stock_repurchased=raw.get("commonStockRepurchased"),
        )


class Financials(BaseModel):
    """Bundled FA output: income + balance + cash flow, last N years."""
    symbol: str
    currency: Optional[str] = None
    income_statements: list[IncomeStatement] = []
    balance_sheets: list[BalanceSheet] = []
    cash_flows: list[CashFlow] = []


# ─── GP ───────────────────────────────────────────────────────────────────────

class PriceBar(BaseModel):
    """Source: FMP /stable/historical-price-eod/full (10 fields)."""
    date: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    vwap: Optional[float] = None

    @classmethod
    def from_fmp(cls, raw: dict) -> "PriceBar":
        return cls(
            date=raw.get("date", ""),
            open=raw.get("open"),
            high=raw.get("high"),
            low=raw.get("low"),
            close=raw.get("close"),
            volume=raw.get("volume"),
            change=raw.get("change"),
            change_percent=raw.get("changePercent"),
            vwap=raw.get("vwap"),
        )


class PriceHistory(BaseModel):
    symbol: str
    currency: Optional[str] = None
    bars: list[PriceBar] = []
    source: Optional[str] = None
    fetched_at: Optional[str] = None


# ─── ANR ──────────────────────────────────────────────────────────────────────

class PriceTarget(BaseModel):
    """Source: FMP /stable/price-target-consensus."""
    symbol: str
    target_high: Optional[float] = None
    target_low: Optional[float] = None
    target_consensus: Optional[float] = None
    target_median: Optional[float] = None

    @classmethod
    def from_fmp(cls, raw: dict) -> "PriceTarget":
        return cls(
            symbol=raw.get("symbol", ""),
            target_high=raw.get("targetHigh"),
            target_low=raw.get("targetLow"),
            target_consensus=raw.get("targetConsensus"),
            target_median=raw.get("targetMedian"),
        )


class AnalystRatings(BaseModel):
    """Bundled ANR output: price targets + consensus rating."""
    symbol: str
    price_target: Optional[PriceTarget] = None
    # Buy/hold/sell breakdown — populated from OpenBB when available
    consensus_rating: Optional[str] = None  # "Buy", "Hold", "Sell"
    num_analysts: Optional[int] = None
    strong_buy: Optional[int] = None
    buy: Optional[int] = None
    hold: Optional[int] = None
    sell: Optional[int] = None
    strong_sell: Optional[int] = None


# ─── COMP ─────────────────────────────────────────────────────────────────────

class PeerProfile(BaseModel):
    """Lightweight profile for a comparable company — sourced from OpenBB."""
    symbol: str
    name: Optional[str] = None
    market_cap: Optional[int] = None
    pe_ratio: Optional[float] = None        # price / eps_diluted
    pb_ratio: Optional[float] = None        # market_cap / total_equity
    fcf_yield: Optional[float] = None       # free_cash_flow / market_cap
    revenue: Optional[int] = None           # from latest income statement
    gross_margin: Optional[float] = None    # gross_profit / revenue  (0-100 scale)
    net_margin: Optional[float] = None      # net_income / revenue    (0-100 scale)
    operating_margin: Optional[float] = None
    ebitda: Optional[int] = None
    total_debt: Optional[int] = None
    beta: Optional[float] = None
    dividend_yield: Optional[float] = None
    currency: Optional[str] = None


class Comparables(BaseModel):
    symbol: str
    peers: list[PeerProfile] = []


# ─── RPT / RV ─────────────────────────────────────────────────────────────────

class FinancialRatios(BaseModel):
    """Computed ratios for one fiscal year."""
    fiscal_year: Optional[str] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    ebitda_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    net_debt_to_ebitda: Optional[float] = None
    current_ratio: Optional[float] = None
    asset_turnover: Optional[float] = None
    fcf_margin: Optional[float] = None


class ValuationMultiples(BaseModel):
    """Market-price-based valuation multiples (computed from live price + FA data)."""
    current_price: Optional[float] = None
    price_date: Optional[str] = None
    market_cap: Optional[int] = None
    enterprise_value: Optional[int] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    ev_to_sales: Optional[float] = None
    fcf_yield: Optional[float] = None
    dividend_yield: Optional[float] = None


class FCFFYear(BaseModel):
    """One year row in the DCF schedule (historical or projected)."""
    year: str
    revenue: Optional[float] = None
    ebit: Optional[float] = None
    tax_rate: Optional[float] = None
    ebit_after_tax: Optional[float] = None
    da: Optional[float] = None
    nwc_change: Optional[float] = None
    capex: Optional[float] = None
    fcff: Optional[float] = None
    pv_factor: Optional[float] = None   # None for historical years
    pv_fcff: Optional[float] = None     # None for historical years


class DCFResult(BaseModel):
    """Full DCF valuation output — WACC inputs, FCFF schedule, equity bridge, sensitivity."""
    # External market inputs
    rf: float                           # 10Y Treasury yield (decimal)
    erp: float                          # Damodaran implied ERP (decimal)
    crp: float = 0.0                    # Country risk premium (0 for US)
    using_fallback_rates: bool = False  # True if Damodaran/Treasury fetch failed

    # Beta & WACC derivation
    beta_raw: Optional[float] = None    # yfinance beta (levered)
    beta_levered: float = 1.0           # beta used in CAPM
    tax_rate: float = 0.21              # average effective tax rate
    cost_of_equity: float = 0.0
    cost_of_debt: float = 0.0
    equity_weight: float = 0.0
    debt_weight: float = 0.0
    wacc: float = 0.0
    terminal_growth: float = 0.025

    # Projection assumptions
    revenue_cagr: float = 0.0
    ebit_margin_avg: float = 0.0

    # FCFF schedule
    fcff_history: list[FCFFYear] = []
    fcff_projections: list[FCFFYear] = []

    # Valuation bridge
    pv_discrete: float = 0.0
    terminal_value: float = 0.0
    pv_terminal: float = 0.0
    enterprise_value_dcf: float = 0.0
    total_debt: float = 0.0
    cash: float = 0.0
    equity_value_dcf: float = 0.0
    shares_outstanding: Optional[int] = None
    dcf_per_share: Optional[float] = None
    current_price: Optional[float] = None
    upside_pct: Optional[float] = None

    # 5×5 sensitivity grid (DCF price per share)
    sensitivity_wacc: list[float] = []   # 5 WACC variants
    sensitivity_tg: list[float] = []     # 5 terminal growth variants
    sensitivity_grid: list[list[float]] = []  # grid[i][j] = price at wacc[i], tg[j]


class InsightsData(BaseModel):
    """AI-generated narrative for the Insights section of the HTML report."""
    what_happened: str = ""
    our_thoughts: str = ""        # 2–3 prose paragraphs as HTML <p> tags
    news_headlines: list[str] = []


class EquityReport(BaseModel):
    """Full RPT output — all layers assembled into one object."""
    symbol: str
    generated_at: str
    profile: Optional[CompanyProfile] = None
    financials: Optional[Financials] = None
    ratios_by_year: list[FinancialRatios] = []
    valuation: Optional[ValuationMultiples] = None
    analyst: Optional[AnalystRatings] = None
    comparables: Optional[Comparables] = None
    quarterly: Optional["QuarterlyFinancials"] = None
    insights: Optional[InsightsData] = None
    trading_metrics: dict = {}    # 52w high/low, avg_daily_volume, avg_daily_value
    financial_row_classification: Optional[dict] = None
    # {"IS": {"Total Revenue": "Revenue", ...}, "BS": {...}, "CF": {...}}
    dcf: Optional[DCFResult] = None


# ─── FX ───────────────────────────────────────────────────────────────────────

class FXRate(BaseModel):
    """Spot rate for a single currency pair."""
    pair: str                          # e.g. "EURUSD"
    base: str                          # e.g. "EUR"
    quote: str                         # e.g. "USD"
    rate: Optional[float] = None       # quote units per 1 base unit
    change_pct: Optional[float] = None # 1-day % change
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    date: Optional[str] = None


class FXBoard(BaseModel):
    """Multi-currency monitor — FXIP output."""
    as_of: str
    rates: list[FXRate] = []


class FXConversion(BaseModel):
    """FXCA output — result of converting an amount between two currencies."""
    from_currency: str
    to_currency: str
    amount: float
    rate: float
    converted: float
    as_of: Optional[str] = None


class FXVolatility(BaseModel):
    """Historical vol for a currency pair over various windows — FXHV output."""
    pair: str
    as_of: Optional[str] = None
    vol_10d: Optional[float] = None    # annualised HV, 0-100 scale
    vol_20d: Optional[float] = None
    vol_30d: Optional[float] = None
    vol_60d: Optional[float] = None
    vol_90d: Optional[float] = None
    vol_180d: Optional[float] = None
    vol_1y: Optional[float] = None
    bars: list[PriceBar] = []          # raw OHLCV so renderer can chart


class FXForwardPoint(BaseModel):
    """One tenor row for FRD output."""
    tenor: str                         # "O/N", "1W", "1M", …
    days: int
    forward_rate: Optional[float] = None
    forward_points: Optional[float] = None  # forward_rate - spot (in pips)
    implied_yield_diff: Optional[float] = None  # annualised %, from CIP


class FXForwardCurve(BaseModel):
    """FRD output — forward curve for one currency pair."""
    pair: str
    spot: Optional[float] = None
    as_of: Optional[str] = None
    tenors: list[FXForwardPoint] = []


class FXRankRow(BaseModel):
    """One row in the WCR currency performance table."""
    currency: str
    pair_vs_usd: str                   # e.g. "EURUSD=X"
    spot: Optional[float] = None
    change_1d: Optional[float] = None
    change_1w: Optional[float] = None
    change_1m: Optional[float] = None
    change_3m: Optional[float] = None
    change_ytd: Optional[float] = None


class FXRanking(BaseModel):
    """WCR output — ranked currencies by performance."""
    as_of: str
    rows: list[FXRankRow] = []


# ─── Quarterly financials ──────────────────────────────────────────────────────

class QuarterlyPeriod(BaseModel):
    """One quarter's worth of financial data for a single statement."""
    date: str                                      # period-end date "2025-03-29"
    fiscal_year: str                               # "2025"
    quarter: str                                   # "Q1" | "Q2" | "Q3" | "Q4"
    fields: dict[str, Optional[float]] = {}        # display_row_name -> value


class QuarterlyFinancials(BaseModel):
    """Quarterly IS / BS / CF periods for XLSX download."""
    symbol: str
    currency: Optional[str] = None
    income:   list[QuarterlyPeriod] = []
    balance:  list[QuarterlyPeriod] = []
    cashflow: list[QuarterlyPeriod] = []
