"Base interface and validation helpers for factor operators."

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod


class Operator(ABC):
    "Base class for operators that require configuration or custom evaluation logic."

    @abstractmethod
    def __call__(self, *args, **kwargs) -> pd.DataFrame:
        raise NotImplementedError

    def __repr__(self):
        return f"{self.__class__.__name__}()"


def validate_matrix(df: pd.DataFrame, name: str = "input"):
    "Validate that the input is a nonempty DataFrame representing a date-by-security matrix."
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{name} must be a DataFrame, got {type(df)}")
    if df.empty:
        raise ValueError(f"{name} DataFrame is empty")
    # Rows represent dates; columns represent security codes
    return df
