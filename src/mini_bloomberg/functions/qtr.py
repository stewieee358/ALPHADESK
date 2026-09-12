from mini_bloomberg.core.errors import MiniBloombergError
from mini_bloomberg.data.equity_quarterly import get_quarterly_financials
from mini_bloomberg.functions.base import BloombergFunction

# Accepted --statement aliases → QuarterlyFinancials field name
_STATEMENT_ALIASES = {
    "IS": "income",   "INCOME": "income",   "I": "income",
    "BS": "balance",  "BALANCE": "balance", "B": "balance",
    "CF": "cashflow", "CASHFLOW": "cashflow", "CASH": "cashflow", "C": "cashflow",
}
_STATEMENT_FIELDS = ("income", "balance", "cashflow")


class QTR(BloombergFunction):
    name = "QTR"
    description = (
        "Quarterly financials: income statement, balance sheet and cash flow "
        "broken out by fiscal quarter (FA covers annual periods only)."
    )

    def run(
        self,
        ticker: str | None = None,
        quarters: int = 8,
        statement: str | None = None,
        **kwargs,
    ) -> dict:
        try:
            t = self._resolve_ticker(ticker)

            try:
                quarters = max(1, min(int(quarters), 40))
            except (TypeError, ValueError):
                quarters = 8

            wanted = None
            if statement:
                wanted = _STATEMENT_ALIASES.get(str(statement).strip().upper())
                if wanted is None:
                    return {
                        "status": "error",
                        "message": f"Unknown statement '{statement}'. Use IS, BS or CF.",
                    }

            data = get_quarterly_financials(t).model_dump()

            # Periods come back oldest-first, so the most recent N are at the tail.
            for field in _STATEMENT_FIELDS:
                if wanted and field != wanted:
                    data[field] = []
                else:
                    data[field] = data.get(field, [])[-quarters:]

            # The SEC path leaves currency unset — fall back to the profile's.
            if not data.get("currency"):
                try:
                    from mini_bloomberg.data.equity_profile import get_profile
                    data["currency"] = get_profile(t).currency
                except Exception:
                    pass

            data["quarters"] = quarters
            data["statement"] = wanted
            return {"status": "ok", "data": data}
        except MiniBloombergError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {e}"}

    def tool_schema(self) -> dict:
        return {
            "name": "qtr",
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Bloomberg-style ticker, e.g. 'AAPL US Equity'",
                    },
                    "quarters": {
                        "type": "integer",
                        "description": "Number of most recent quarters to return (default 8, max 40)",
                        "default": 8,
                    },
                    "statement": {
                        "type": "string",
                        "description": "Limit output to one statement: 'IS', 'BS' or 'CF'. Omit for all three.",
                        "enum": ["IS", "BS", "CF"],
                    },
                },
                "required": ["ticker"],
            },
        }
