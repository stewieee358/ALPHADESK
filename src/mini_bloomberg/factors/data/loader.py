"Load date-by-security matrices from Tushare, JoinQuant, local CSV files or existing DataFrames. Provider SDKs are optional and imported only when used."

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from ..core.context import Context


class DataLoader:
    "Load data from a supported provider, a local CSV file, or an existing mapping of DataFrames."

    def __init__(self, source: str = "local", token: str = None):
        self.source = source
        self.token = token

    def load(
        self,
        stock_list: List[str],
        start_date: str,
        end_date: str,
        fields: List[str] = None,
    ) -> Context:
        "Dispatch to the configured provider and return a Context. Local data must use from_csv or from_dataframe."
        if self.source == "tushare":
            return self._load_tushare(stock_list, start_date, end_date, fields)
        elif self.source == "joinquant":
            return self._load_joinquant(stock_list, start_date, end_date, fields)
        elif self.source == "local":
            raise ValueError("Use DataLoader.from_csv() or from_dataframe() for local data.")
        else:
            raise ValueError(f"Unknown data source: {self.source}")

    # -----------------------------------------------------------------------
    # Tushare
    # -----------------------------------------------------------------------
    def _load_tushare(
        self, stock_list, start_date, end_date, fields
    ) -> Context:
        "Load Tushare daily data for stock_list and the requested dates. Requires the optional tushare package and a valid token. Map vol to volume and derive returns from close."
        try:
            import tushare as ts
        except ImportError:
            raise ImportError("Install the optional Tushare SDK first: pip install tushare")

        ts.set_token(self.token)
        pro = ts.pro_api()

        if fields is None:
            fields = ["close", "open", "high", "low", "vol", "amount"]

        # Tushare field mapping
        ts_field_map = {
            "close": "close", "open": "open", "high": "high", "low": "low",
            "volume": "vol", "vol": "vol", "amount": "amount",
        }

        all_data = []
        for ts_code in stock_list:
            df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                df["trade_date"] = pd.to_datetime(df["trade_date"])
                df = df.set_index("trade_date").sort_index()
                df["stock"] = ts_code
                all_data.append(df)

        if not all_data:
            raise ValueError("No data loaded from tushare")

        combined = pd.concat(all_data)

        # Convert to date-by-security matrices
        ctx = Context()
        field_mapping = {"vol": "volume"}  # Normalize field names

        for field in fields:
            ts_field = ts_field_map.get(field, field)
            if ts_field in combined.columns:
                pivot = combined.pivot_table(
                    index=combined.index, columns="stock", values=ts_field
                )
                unified_name = field_mapping.get(field, field)
                ctx[unified_name] = pivot

        # Calculate derived fields
        if "close" in ctx:
            ctx.add_derived("returns", ctx["close"].pct_change(fill_method=None))
        if "amount" in ctx and "volume" in ctx:
            vwap = ctx["amount"] / ctx["volume"].replace(0, np.nan)
            ctx.add_derived("vwap", vwap)

        return ctx

    # -----------------------------------------------------------------------
    # JoinQuant
    # -----------------------------------------------------------------------
    def _load_joinquant(
        self, stock_list, start_date, end_date, fields
    ) -> Context:
        "Load daily prices from JoinQuant. Requires the optional jqdatasdk package. The token, when supplied, has the form username:password."
        try:
            from jqdatasdk import auth, get_price
        except ImportError:
            raise ImportError("Install the optional JoinQuant SDK first: pip install jqdatasdk")

        # JoinQuant authentication uses a token formatted as "user:pass"
        if self.token and ":" in self.token:
            user, pwd = self.token.split(":", 1)
            auth(user, pwd)

        if fields is None:
            fields = ["close", "open", "high", "low", "volume", "money"]

        df = get_price(
            stock_list,
            start_date=start_date,
            end_date=end_date,
            frequency="daily",
            fields=fields,
            panel=False,
        )

        ctx = Context()
        field_mapping = {"money": "amount"}

        for field in fields:
            if field in df.columns:
                pivot = df.pivot_table(index="time", columns="code", values=field)
                unified_name = field_mapping.get(field, field)
                ctx[unified_name] = pivot

        if "close" in ctx:
            ctx.add_derived("returns", ctx["close"].pct_change(fill_method=None))

        return ctx

    # -----------------------------------------------------------------------
    # Load local data
    # -----------------------------------------------------------------------
    @staticmethod
    def from_dataframe(data_dict: Dict[str, pd.DataFrame]) -> Context:
        "Create a Context from {field_name: DataFrame}, with dates as rows and security codes as columns. Derive returns from close when returns is absent."
        ctx = Context()
        ctx.load_from_dict(data_dict)

        if "close" in ctx and "returns" not in ctx:
            ctx.add_derived("returns", ctx["close"].pct_change(fill_method=None))

        return ctx

    @staticmethod
    def from_csv(
        filepath: str,
        date_col: str = "trade_date",
        stock_col: str = "ts_code",
        fields: List[str] = None,
    ) -> Context:
        "Load a long-format CSV with date and security columns plus numeric data fields. Defaults: trade_date and ts_code. Example header: trade_date,ts_code,close,open,high,low,volume. Each date/security pair must be unique."
        df = pd.read_csv(filepath, dtype={stock_col: str})
        df[date_col] = pd.to_datetime(df[date_col].astype(str), errors="raise")
        if df.empty or df[[date_col, stock_col]].isna().any().any():
            raise ValueError("CSV must contain nonempty dates and security codes")
        if df.duplicated([date_col, stock_col]).any():
            raise ValueError("Duplicate date/security rows in CSV")

        if fields is None:
            fields = [c for c in df.columns if c not in [date_col, stock_col]]

        ctx = Context()
        for field in fields:
            if field in df.columns:
                pivot = df.pivot(index=date_col, columns=stock_col, values=field).sort_index()
                ctx[field] = pivot

        if "close" in ctx and "returns" not in ctx:
            ctx.add_derived("returns", ctx["close"].pct_change(fill_method=None))

        return ctx
