from datetime import date

from mini_bloomberg.core.errors import MiniBloombergError
from mini_bloomberg.data.equity_dcf import compute_dcf
from mini_bloomberg.data.equity_fundamentals import get_financials
from mini_bloomberg.data.equity_price import get_price_history
from mini_bloomberg.data.equity_profile import get_profile
from mini_bloomberg.data.schemas import EquityReport
from mini_bloomberg.functions.base import BloombergFunction


class DCF(BloombergFunction):
    name = "DCF"
    description = (
        "Discounted cash flow valuation: WACC derivation, historical and projected FCFF, "
        "terminal value, implied fair value per share vs. current price, and a "
        "WACC x terminal-growth sensitivity grid."
    )

    def run(self, ticker: str | None = None, years: int = 4, **kwargs) -> dict:
        try:
            t = self._resolve_ticker(ticker)

            # compute_dcf() consumes an EquityReport, but only needs profile +
            # financials — build a minimal one to skip RPT's LLM insight calls.
            report = EquityReport(symbol=t.symbol, generated_at=date.today().isoformat())
            report.profile = get_profile(t)
            report.financials = get_financials(t, years=years)

            current_price = None
            try:
                history = get_price_history(t, days=5)
                if history.bars:
                    current_price = history.bars[-1].close
            except Exception:
                pass

            result = compute_dcf(report, current_price)
            if result is None:
                return {
                    "status": "error",
                    "message": f"DCF could not be computed for {t} — insufficient financial data.",
                }

            data = result.model_dump()
            data["symbol"] = t.symbol
            data["currency"] = report.profile.currency if report.profile else None
            return {"status": "ok", "data": data}
        except MiniBloombergError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {e}"}

    def tool_schema(self) -> dict:
        return {
            "name": "dcf",
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Bloomberg-style ticker, e.g. 'AAPL US Equity'",
                    },
                    "years": {
                        "type": "integer",
                        "description": "Annual periods of history used to derive the projection (default 4)",
                        "default": 4,
                    },
                },
                "required": ["ticker"],
            },
        }
