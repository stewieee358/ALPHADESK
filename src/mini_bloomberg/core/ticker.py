"""
Parse Bloomberg-style ticker strings into a structured Ticker model.

Supported formats:
  "AAPL US Equity"    → symbol=AAPL, exchange=US, asset_class=Equity
  "0700 HK Equity"    → symbol=0700, exchange=HK, asset_class=Equity
  "7203 JP Equity"    → symbol=7203, exchange=JP, asset_class=Equity
  "MC FP Equity"      → symbol=MC,   exchange=FP, asset_class=Equity
  "AAPL"              → symbol=AAPL, exchange=US, asset_class=Equity (default)
"""

from pydantic import BaseModel

from mini_bloomberg.core.errors import TickerError

# Exchange codes that indicate US-listed equities
US_EXCHANGE_CODES = {"US", "UN", "UW", "UA", "UQ"}

# Map Bloomberg exchange codes → yfinance suffix for non-US tickers
EXCHANGE_TO_YFINANCE: dict[str, str] = {
    "HK": ".HK",
    "JP": ".T",
    "FP": ".PA",   # Paris (Euronext)
    "GR": ".DE",   # Germany (XETRA)
    "LN": ".L",    # London
    "AU": ".AX",   # Australia
    "CN": ".SS",   # Shanghai (A-shares — limited coverage)
    "CH": ".SS",   # China; suffix is inferred from the numeric symbol below
    "SH": ".SS",
    "SZ": ".SZ",
    "BJ": ".BJ",
    "KS": ".KS",   # Korea
    "IN": ".NS",   # India NSE
    "SP": ".SI",   # Singapore
}


class Ticker(BaseModel):
    symbol: str
    exchange_code: str  # Bloomberg exchange code, e.g. "US", "HK", "JP"
    asset_class: str    # "Equity" (only supported asset class in v1)

    @property
    def is_us(self) -> bool:
        return self.exchange_code in US_EXCHANGE_CODES

    @property
    def is_china(self) -> bool:
        return self.exchange_code in {"CH", "CN", "SH", "SZ", "BJ"}

    @property
    def tushare_symbol(self) -> str:
        """Convert a China equity ticker to Tushare's 000001.SZ format."""
        if not self.is_china:
            return self.symbol
        exchange = self.exchange_code
        if exchange in {"CH", "CN"}:
            if self.symbol.startswith(("4", "8")):
                exchange = "BJ"
            elif self.symbol.startswith(("0", "3")):
                exchange = "SZ"
            else:
                exchange = "SH"
        return f"{self.symbol}.{exchange}"

    @property
    def yfinance_symbol(self) -> str:
        """Convert to yfinance-compatible symbol, e.g. '7203.T', '0700.HK'."""
        if self.is_us:
            return self.symbol
        exchange = self.exchange_code
        if exchange in {"CH", "CN"}:
            exchange = self.tushare_symbol.rsplit(".", 1)[-1]
        suffix = EXCHANGE_TO_YFINANCE.get(exchange, "")
        sym = self.symbol
        # HKEX 5-digit display codes (e.g. 09988, 03993) have a padding leading zero;
        # yfinance uses the underlying 4-digit code (9988.HK, 3993.HK).
        if self.exchange_code == "HK" and len(sym) == 5 and sym.startswith("0"):
            sym = sym[1:]
        return f"{sym}{suffix}" if suffix else sym

    @property
    def fmp_symbol(self) -> str:
        """FMP uses plain symbol for US and exchange-suffixed for non-US (e.g. 3693.HK, 7203.T)."""
        if self.is_us:
            return self.symbol
        suffix = EXCHANGE_TO_YFINANCE.get(self.exchange_code, "")
        sym = self.symbol
        # Strip HKEX display leading zero (same logic as yfinance_symbol)
        if self.exchange_code == "HK" and len(sym) == 5 and sym.startswith("0"):
            sym = sym[1:]
        return f"{sym}{suffix}" if suffix else sym

    def __str__(self) -> str:
        return f"{self.symbol} {self.exchange_code} {self.asset_class}"


def parse_ticker(raw: str) -> Ticker:
    """
    Parse a Bloomberg-style ticker string.
    Raises TickerError on invalid input.
    """
    if not raw or not raw.strip():
        raise TickerError("Ticker string is empty")

    parts = raw.strip().split()

    if len(parts) == 1:
        # Bare symbol — assume US Equity
        return Ticker(symbol=parts[0].upper(), exchange_code="US", asset_class="Equity")

    if len(parts) == 2:
        # "AAPL US" — assume Equity
        return Ticker(symbol=parts[0].upper(), exchange_code=parts[1].upper(), asset_class="Equity")

    if len(parts) == 3:
        asset_class = parts[2].capitalize()
        if asset_class not in ("Equity",):
            raise TickerError(
                f"Unsupported asset class '{parts[2]}'. Only Equity is supported in v1."
            )
        return Ticker(symbol=parts[0].upper(), exchange_code=parts[1].upper(), asset_class=asset_class)

    raise TickerError(
        f"Cannot parse ticker '{raw}'. Expected format: 'AAPL US Equity'"
    )
