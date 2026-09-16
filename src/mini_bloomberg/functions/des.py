from mini_bloomberg.core.errors import MiniBloombergError
from mini_bloomberg.data.equity_price import get_price_history
from mini_bloomberg.data.equity_profile import get_profile
from mini_bloomberg.functions.base import BloombergFunction


class DES(BloombergFunction):
    name = "DES"
    description = "Company description: name, sector, exchange, market cap, and key identifiers."

    def run(self, ticker: str | None = None, **kwargs) -> dict:
        try:
            t = self._resolve_ticker(ticker)
            profile = get_profile(t)
            data = profile.model_dump()

            # Augment with live price and change
            try:
                history = get_price_history(t, days=5)
                if history.bars:
                    last = history.bars[-1]
                    data["last_price"] = last.close
                    data["change_pct"] = last.change_percent
            except Exception:
                pass

            # Augment with provider-native valuation metrics.
            if t.is_china:
                try:
                    from mini_bloomberg.data.providers.tushare_provider import get_daily_metrics
                    data.update({k: v for k, v in get_daily_metrics(t).items()
                                 if k in {"pe_ratio", "pb_ratio", "ps_ratio"}})
                except Exception:
                    pass
            else:
                try:
                    import yfinance as yf
                    info = yf.Ticker(t.yfinance_symbol).info
                    data["pe_ratio"] = info.get("trailingPE")
                    data["ev_to_ebitda"] = info.get("enterpriseToEbitda")
                except Exception:
                    pass

            return {"status": "ok", "data": data}
        except MiniBloombergError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {e}"}

    def tool_schema(self) -> dict:
        return {
            "name": "des",
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Bloomberg-style ticker, e.g. 'AAPL US Equity' or '0700 HK Equity'",
                    }
                },
                "required": ["ticker"],
            },
        }
