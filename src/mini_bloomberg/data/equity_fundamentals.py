"""
Fundamentals router: FMP for US tickers, OpenBB fallback for non-US.
"""

from mini_bloomberg.core.errors import DataSourceError
from mini_bloomberg.core.ticker import Ticker
from mini_bloomberg.data.providers import fmp_provider, openbb_provider, tushare_provider
from mini_bloomberg.data.schemas import BalanceSheet, CashFlow, Financials, IncomeStatement

# yfinance does not return a currency field in fundamentals; derive from exchange code
_EXCHANGE_CURRENCY: dict[str, str] = {
    "HK": "HKD", "JP": "JPY", "FP": "EUR", "GR": "EUR",
    "LN": "GBP", "AU": "AUD", "KS": "KRW", "IN": "INR", "SP": "SGD",
}


def _int(v) -> int | None:
    """yfinance returns large monetary values as floats with fractional parts; coerce to int."""
    if v is None:
        return None
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def get_financials(ticker: Ticker, years: int = 4) -> Financials:
    if ticker.is_china:
        return tushare_provider.get_financials(ticker, years=years)
    if ticker.is_us:
        try:
            return _from_fmp(ticker, years)
        except DataSourceError:
            pass  # fall through to OpenBB
    else:
        # Non-US: try yfinance first (broader non-US coverage)
        try:
            result = _from_openbb(ticker, years)
            if result.income_statements:
                return result
        except Exception:
            pass
        # yfinance had no data — try FMP (covers major HK/JP/EU stocks with suffix symbol)
        try:
            return _from_fmp(ticker, years)
        except DataSourceError:
            pass
        raise DataSourceError(f"All fundamentals providers failed for {ticker}")

    try:
        return _from_openbb(ticker, years)
    except Exception as e:
        raise DataSourceError(f"All fundamentals providers failed for {ticker}: {e}") from e


def _from_fmp(ticker: Ticker, years: int) -> Financials:
    income   = fmp_provider.get_income_statements(ticker, limit=years)
    balance  = fmp_provider.get_balance_sheets(ticker, limit=years)
    cashflow = fmp_provider.get_cash_flows(ticker, limit=years)
    currency = income[0].reported_currency if income else None
    return Financials(
        symbol=ticker.symbol,
        currency=currency,
        income_statements=income,
        balance_sheets=balance,
        cash_flows=cashflow,
    )


def _from_openbb(ticker: Ticker, years: int) -> Financials:
    obb = openbb_provider._obb()
    sym = ticker.yfinance_symbol
    kwargs = dict(symbol=sym, provider="yfinance", period="annual", limit=years)

    # Request one extra for income: yfinance sometimes prepends a forward/TTM row with no
    # revenue/net_income (only EPS estimates), which we filter out below.
    inc_raw = openbb_provider._all(obb.equity.fundamental.income(
        symbol=sym, provider="yfinance", period="annual", limit=years + 1
    ))
    bal_raw = openbb_provider._all(obb.equity.fundamental.balance(**kwargs))
    cf_raw  = openbb_provider._all(obb.equity.fundamental.cash(**kwargs))

    # Drop rows that have no actual financial data (forward/estimate rows)
    inc_raw = [
        r for r in inc_raw
        if r.get("total_revenue") or r.get("net_income") or r.get("gross_profit")
    ][:years]

    currency = (
        (inc_raw[0].get("reported_currency") or inc_raw[0].get("currency"))
        if inc_raw else None
    ) or _EXCHANGE_CURRENCY.get(ticker.exchange_code)

    def _date(r: dict) -> str:
        # yfinance uses period_ending (datetime.date); legacy providers use date
        d = r.get("period_ending") or r.get("date") or ""
        return str(d)[:10]

    def _year(r: dict) -> str:
        return _date(r)[:4]

    def _income(r: dict) -> IncomeStatement:
        return IncomeStatement(
            symbol=ticker.symbol,
            date=_date(r),
            fiscal_year=_year(r),
            period="FY",
            reported_currency=currency,
            revenue=_int(r.get("total_revenue") or r.get("revenue") or r.get("operating_revenue")),
            cost_of_revenue=_int(r.get("cost_of_revenue") or r.get("reconciled_cost_of_revenue")),
            gross_profit=_int(r.get("gross_profit")),
            operating_expenses=_int(r.get("operating_expense") or r.get("total_expenses")),
            operating_income=_int(r.get("operating_income") or r.get("ebit")),
            ebitda=_int(r.get("ebitda") or r.get("normalized_ebitda")),
            ebit=_int(r.get("ebit")),
            net_income=_int(r.get("net_income") or r.get("net_income_continuous_operations")),
            eps=r.get("basic_earnings_per_share") or r.get("eps"),
            eps_diluted=r.get("diluted_earnings_per_share") or r.get("eps_diluted"),
            rd_expenses=_int(r.get("research_and_development") or r.get("research_and_development_expenses")),
            sga_expenses=_int(r.get("selling_general_and_admin_expense") or r.get("selling_general_and_administrative_expenses")),
            income_tax_expense=_int(r.get("tax_provision") or r.get("income_tax_expense")),
            interest_expense=_int(r.get("interest_expense") or r.get("interest_expense_non_operating")),
            depreciation_and_amortization=_int(r.get("reconciled_depreciation") or r.get("depreciation_and_amortization")),
            weighted_avg_shares=_int(r.get("weighted_average_basic_shares_outstanding") or r.get("weighted_average_shares")),
            weighted_avg_shares_diluted=_int(r.get("weighted_average_diluted_shares_outstanding") or r.get("weighted_average_shares_diluted")),
        )

    def _balance(r: dict) -> BalanceSheet:
        cash = _int(r.get("cash_and_cash_equivalents") or r.get("cash_financial") or r.get("cash"))
        total_debt = _int(r.get("total_debt"))
        net_debt = _int(r.get("net_debt"))
        if net_debt is None and total_debt is not None and cash is not None:
            net_debt = total_debt - cash
        return BalanceSheet(
            symbol=ticker.symbol,
            date=_date(r),
            fiscal_year=_year(r),
            period="FY",
            reported_currency=currency,
            cash_and_equivalents=cash,
            short_term_investments=_int(r.get("short_term_investments")),
            net_receivables=_int(r.get("accounts_receivable") or r.get("net_receivables") or r.get("receivables")),
            inventory=_int(r.get("inventories") or r.get("inventory")),
            total_current_assets=_int(r.get("total_current_assets")),
            total_non_current_assets=_int(r.get("total_non_current_assets")),
            total_assets=_int(r.get("total_assets")),
            accounts_payable=_int(r.get("accounts_payable") or r.get("payables")),
            short_term_debt=_int(r.get("current_debt") or r.get("short_term_debt") or r.get("current_debt_and_capital_lease_obligation")),
            total_current_liabilities=_int(r.get("current_liabilities") or r.get("total_current_liabilities")),
            long_term_debt=_int(r.get("long_term_debt") or r.get("long_term_debt_and_capital_lease_obligation")),
            total_non_current_liabilities=_int(r.get("total_non_current_liabilities_net_minority_interest") or r.get("total_non_current_liabilities")),
            total_liabilities=_int(r.get("total_liabilities_net_minority_interest") or r.get("total_liabilities")),
            total_stockholders_equity=_int(r.get("total_common_equity") or r.get("common_stock_equity") or r.get("total_stockholder_equity")),
            total_equity=_int(r.get("total_equity_non_controlling_interests") or r.get("total_common_equity")),
            total_debt=total_debt,
            net_debt=net_debt,
            goodwill=_int(r.get("goodwill")),
            retained_earnings=_int(r.get("retained_earnings")),
        )

    def _cf(r: dict) -> CashFlow:
        return CashFlow(
            symbol=ticker.symbol,
            date=_date(r),
            fiscal_year=_year(r),
            period="FY",
            reported_currency=currency,
            net_income=_int(r.get("net_income_from_continuing_operations") or r.get("net_income")),
            depreciation_and_amortization=_int(r.get("depreciation_and_amortization") or r.get("depreciation")),
            stock_based_compensation=_int(r.get("stock_based_compensation") or r.get("share_based_compensation")),
            change_in_working_capital=_int(r.get("change_in_working_capital")),
            operating_cash_flow=_int(r.get("operating_cash_flow") or r.get("total_cash_from_operating_activities")),
            capital_expenditure=_int(r.get("capital_expenditure") or r.get("capital_expenditures") or r.get("investments_in_property_plant_and_equipment")),
            free_cash_flow=_int(r.get("free_cash_flow")),
            net_investing_activities=_int(r.get("investing_cash_flow") or r.get("net_investing_activities") or r.get("net_cash_provided_by_investing_activities")),
            net_financing_activities=_int(r.get("financing_cash_flow") or r.get("net_financing_activities") or r.get("net_cash_provided_by_financing_activities")),
            net_change_in_cash=_int(r.get("net_change_in_cash_and_equivalents") or r.get("net_change_in_cash")),
            dividends_paid=_int(r.get("cash_dividends_paid") or r.get("common_stock_dividend_paid") or r.get("dividends_paid") or r.get("payment_of_dividends")),
            common_stock_repurchased=_int(r.get("repurchase_of_capital_stock") or r.get("common_stock_repurchased") or r.get("purchase_of_business")),
        )

    return Financials(
        symbol=ticker.symbol,
        currency=currency,
        income_statements=[_income(r) for r in inc_raw],
        balance_sheets=[_balance(r) for r in bal_raw],
        cash_flows=[_cf(r) for r in cf_raw],
    )
