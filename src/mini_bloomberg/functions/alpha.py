"""Factor research exposed through the common MINIBB function interface."""
from pathlib import Path
import math
import re

from pydantic import BaseModel, Field
from .base import BloombergFunction
from mini_bloomberg.data.factor_prices import DEFAULT_SYMBOLS


class AlphaResult(BaseModel):
    dataset: str
    expression: str
    dates: int = 0
    securities: int = 0
    coverage: float = 0
    metrics: dict[str, float | None] = Field(default_factory=dict)
    latest: list[dict] = Field(default_factory=list)
    curve: list[dict] = Field(default_factory=list)
    operators: list[str] = Field(default_factory=list)
    operator_details: list[dict] = Field(default_factory=list)
    fields: list[dict] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    requested_start: str | None = None
    requested_end: str | None = None
    first_date: str | None = None
    last_date: str | None = None


def parse_alpha_args(args):
    try:
        text = " ".join(args).strip()
        if not text:
            return {}
        tokens = re.split(r"(?:^|\s+)--([a-z-]+)(?=\s|$)", text)
        if tokens[0]:
            raise ValueError("ALPHA arguments must use --expression, --dataset or --operators")
        result = {}
        for key, value in zip(tokens[1::2], tokens[2::2]):
            value = value.strip()
            if key == "operators" and not value:
                result["mode"] = "operators"
            elif key in ("expression", "dataset", "symbols", "days", "start", "end"):
                if not value: raise ValueError(f"Missing --{key} value")
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                result[key] = int(value) if key == "days" else value
            else:
                raise ValueError("Use ALPHA --symbols AAPL,MSFT,... --days 365 --expression rank(ts_delta(close, 5))")
        return result
    except ValueError as exc:
        return {"input_error": str(exc)}


class ALPHA(BloombergFunction):
    name = "ALPHA"
    description = "Evaluate factors on online daily equity histories via existing FMP/OpenBB sources; calculate IC and quintile returns. Defaults to a 12-stock US example universe, not the loaded single security."

    def tool_schema(self):
        return {"name": "alpha", "description": self.description, "input_schema": {
            "type": "object", "properties": {
                "expression": {"type": "string", "description": "Factor expression, e.g. rank(ts_delta(close, 5))"},
                "dataset": {"type": "string", "description": "market (default), demo, or CSV filename inside MINIBB/data/factors"},
                "symbols": {"type": "string", "description": "10–50 comma-separated tickers; bare US symbols or Bloomberg format, e.g. AAPL US Equity,0700 HK Equity,..."},
                "days": {"type": "integer", "minimum": 7, "maximum": 1825, "description": "Calendar-day lookback ending at end (default 365)"},
                "start": {"type": "string", "description": "Inclusive start date YYYY-MM-DD; overrides days"},
                "end": {"type": "string", "description": "Inclusive end date YYYY-MM-DD; defaults to today"},
                "mode": {"type": "string", "enum": ["evaluate", "operators"]},
            }, "additionalProperties": False}}

    def run(self, ticker=None, expression="rank(ts_delta(close, 5))", dataset="market", mode="evaluate", input_error=None,
            symbols=DEFAULT_SYMBOLS, days=365, start=None, end=None, **kwargs):
        try:
            if input_error: raise ValueError(input_error)
            if kwargs: raise ValueError(f"Unknown arguments: {', '.join(kwargs)}")
            import numpy as np
            import pandas as pd
            from mini_bloomberg.factors import ExpressionEngine, DataLoader, FactorEvaluator
            from mini_bloomberg.factors.utils.registry import list_operators
            if mode == "operators":
                from mini_bloomberg.factors.catalog import operator_catalog, field_catalog
                output = AlphaResult(dataset=dataset, expression="", operators=sorted(list_operators()),
                    operator_details=operator_catalog(), fields=field_catalog(),
                    notes=["Recovered local implementations; BRAIN equivalence is not certified."])
                return {"status": "ok", "data": output.model_dump()}
            if mode != "evaluate": raise ValueError("mode must be evaluate or operators")
            market = None
            if dataset == "market":
                from mini_bloomberg.data.factor_prices import load_factor_prices
                market = load_factor_prices(symbols=symbols, days=days, start=start, end=end)
                frames = {}
                for name, history in market.histories.items():
                    frame = pd.DataFrame([bar.model_dump() for bar in history.bars])
                    frame.index = pd.to_datetime(frame.pop("date"))
                    frames[name] = frame
                # Union of observed sessions. Never fill across holidays or missing prices.
                matrices = {field: pd.DataFrame({name: frame[field] for name, frame in frames.items()}).sort_index()
                            for field in ("close", "open", "high", "low", "volume", "vwap")}
                ctx = DataLoader.from_dataframe(matrices)
            elif dataset == "demo":
                rng = np.random.default_rng(42)
                dates = pd.bdate_range("2024-01-01", periods=252)
                columns = [f"DEMO{i:02}" for i in range(20)]
                close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0.0002, 0.015, (252, 20)), axis=0)), index=dates, columns=columns)
                ctx = DataLoader.from_dataframe({"close": close, "open": close * 0.999,
                    "high": close * 1.01, "low": close * 0.99,
                    "volume": pd.DataFrame(rng.uniform(1e5, 1e6, (252, 20)), index=dates, columns=columns)})
            else:
                root = Path(__file__).resolve().parents[3] / "data" / "factors"
                target = (root / dataset).resolve()
                if target.parent != root.resolve() or target.suffix.lower() != ".csv":
                    raise ValueError("Choose a CSV filename inside MINIBB/data/factors")
                if not target.is_file(): raise ValueError(f"Dataset not found in data/factors: {target.name}")
                if target.stat().st_size > 20_000_000: raise ValueError("CSV limit is 20 MB")
                ctx = DataLoader.from_csv(str(target))
            if "close" not in ctx: raise ValueError("Dataset requires a close column")
            if len(ctx.stocks) < 10 or len(ctx.dates) < 3:
                raise ValueError("Evaluation requires at least 10 securities and 3 dates")
            if len(ctx.stocks) > 500 or len(ctx.dates) > 5000:
                raise ValueError("Research limit: 500 securities and 5000 dates")
            factor = ExpressionEngine(ctx).evaluate(expression)
            if not isinstance(factor, pd.DataFrame) or not factor.index.equals(ctx.dates) or not factor.columns.equals(ctx.stocks):
                raise ValueError("Expression must produce a date × security matrix")
            factor = factor.replace([np.inf, -np.inf], np.nan)
            if not factor.notna().any().any(): raise ValueError("Expression produced no finite factor values")
            # Derive evaluation returns from close, never trust a supplied forward-return field.
            evaluator = FactorEvaluator(factor, ctx["close"].pct_change(fill_method=None))
            clean = lambda v: float(v) if math.isfinite(float(v)) else None
            metrics = {k: clean(v) for k, v in evaluator.ic_summary().items()}
            latest = [{"security": str(k), "factor": clean(v)} for k, v in factor.iloc[-1].sort_values(ascending=False).items()]
            curve = [{"date": str(date.date()), **{k: clean(v) for k, v in row.items()}}
                     for date, row in evaluator.cumulative_layered_returns().iterrows()]
            output = AlphaResult(dataset=dataset, expression=expression, dates=len(ctx.dates), securities=len(ctx.stocks),
                coverage=float(factor.notna().to_numpy().mean()), metrics=metrics, latest=latest, curve=curve,
                fields=[{"name": name, "coverage": float(ctx[name].replace([np.inf, -np.inf], np.nan).notna().to_numpy().mean())}
                        for name in ctx.fields],
                sources=market.sources if market else [],
                requested_start=market.requested_start if market else None,
                requested_end=market.requested_end if market else None,
                first_date=str(ctx.dates[0].date()), last_date=str(ctx.dates[-1].date()),
                notes=(market.notes if market else ["SYNTHETIC DEMO — not market data." if dataset == "demo" else "User-supplied CSV; verify adjustment and point-in-time universe."]) + [
                    "Signal at close T is paired with close T to T+1 return. Diagnostic gross returns, no costs or execution model.",
                    "IC requires 10 valid securities per date. Recovered operators are not certified BRAIN equivalents."])
            return {"status": "ok", "data": output.model_dump()}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}
