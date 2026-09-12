"Data context holding aligned date-by-security matrices and metadata. Example: ctx.load_from_dict({\"close\": close_df, \"volume\": volume_df})."

import pandas as pd
from typing import Dict, Optional, List


class Context:
    "Manage date-by-security data matrices and associated metadata."

    def __init__(self):
        self._data: Dict[str, pd.DataFrame] = {}
        self._meta: Dict[str, dict] = {}  # Metadata, such as industry classifications

    def __getitem__(self, key: str) -> pd.DataFrame:
        if key not in self._data:
            raise KeyError(f"Data field '{key}' not found. Available: {self.fields}")
        return self._data[key]

    def __setitem__(self, key: str, value: pd.DataFrame):
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    @property
    def fields(self) -> List[str]:
        "Return the names of all loaded data fields."
        return list(self._data.keys())

    @property
    def dates(self) -> Optional[pd.DatetimeIndex]:
        "Return the index of the first loaded matrix, or None if no data is loaded."
        if self._data:
            first = next(iter(self._data.values()))
            return first.index
        return None

    @property
    def stocks(self) -> Optional[pd.Index]:
        "Return the columns of the first loaded matrix, or None if no data is loaded."
        if self._data:
            first = next(iter(self._data.values()))
            return first.columns
        return None

    def load_from_dict(self, data_dict: Dict[str, pd.DataFrame]):
        "Load a mapping of field names to DataFrames. Align subsequent matrices to the first matrix's index and columns; absent observations become missing."
        ref_index = None
        ref_columns = None

        for name, df in data_dict.items():
            if not isinstance(df, pd.DataFrame):
                raise TypeError(f"'{name}' must be a DataFrame")

            if ref_index is None:
                ref_index = df.index
                ref_columns = df.columns
            else:
                if not df.index.equals(ref_index):
                    # Align to the reference date index
                    df = df.reindex(ref_index)
                if not df.columns.equals(ref_columns):
                    df = df.reindex(columns=ref_columns)

            self._data[name] = df

    def add_derived(self, name: str, df: pd.DataFrame):
        "Store a derived matrix such as returns or vwap without additional alignment validation."
        self._data[name] = df

    def set_meta(self, key: str, value: dict):
        "Store metadata, such as an industry mapping, under the given key."
        self._meta[key] = value

    def get_meta(self, key: str) -> dict:
        return self._meta.get(key, {})

    def summary(self) -> str:
        "Return a summary of dates, securities, fields, matrix shapes and missing-value percentages."
        lines = [f"Context: {len(self._data)} fields"]
        if self.dates is not None:
            lines.append(f"  Dates:  {self.dates[0]} ~ {self.dates[-1]} ({len(self.dates)} days)")
        if self.stocks is not None:
            lines.append(f"  Stocks: {len(self.stocks)} stocks")
        for name, df in self._data.items():
            nan_pct = df.isna().sum().sum() / df.size * 100
            lines.append(f"  [{name}] shape={df.shape}, NaN={nan_pct:.1f}%")
        return "\n".join(lines)

    def __repr__(self):
        return self.summary()
