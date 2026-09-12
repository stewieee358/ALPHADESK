from mini_bloomberg.core.errors import MiniBloombergError
from mini_bloomberg.data.equity_news import fetch_company_news
from mini_bloomberg.functions.base import BloombergFunction


class NEWS(BloombergFunction):
    name = "NEWS"
    description = "Recent company news headlines with publication date and summary text."

    def run(self, ticker: str | None = None, limit: int = 10, **kwargs) -> dict:
        try:
            t = self._resolve_ticker(ticker)
            try:
                limit = max(1, min(int(limit), 50))
            except (TypeError, ValueError):
                limit = 10

            articles = fetch_company_news(t, limit=limit)
            return {
                "status": "ok",
                "data": {
                    "symbol": t.symbol,
                    "count": len(articles),
                    "articles": articles,
                },
            }
        except MiniBloombergError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {e}"}

    def tool_schema(self) -> dict:
        return {
            "name": "news",
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Bloomberg-style ticker, e.g. 'AAPL US Equity'",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of headlines to return (default 10, max 50)",
                        "default": 10,
                    },
                },
                "required": ["ticker"],
            },
        }
