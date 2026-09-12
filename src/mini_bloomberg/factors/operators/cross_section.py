"Cross-sectional operators apply independently across securities on each date: ranking, standardization, scaling, demeaning, winsorization and group neutralization."

import pandas as pd
import numpy as np
from ..utils.registry import register_operator


# ---------------------------------------------------------------------------
# rank: cross-sectional percentile ranking
# ---------------------------------------------------------------------------
@register_operator("rank")
def rank(df: pd.DataFrame) -> pd.DataFrame:
    "Cross-sectional percentile rank, independently for each date. For example, rank(close) ranks closing prices across securities. Missing observations remain missing; ties use the pandas ranking default."
    return df.rank(axis=1, pct=True)


# ---------------------------------------------------------------------------
# zscore: cross-sectional standardization
# ---------------------------------------------------------------------------
@register_operator("zscore")
def zscore(df: pd.DataFrame) -> pd.DataFrame:
    "Cross-sectional standardization: (x - row mean) / row standard deviation."
    mean = df.mean(axis=1)
    std = df.std(axis=1)
    std = std.replace(0, np.nan)  # Avoid division by zero
    return df.sub(mean, axis=0).div(std, axis=0)


# ---------------------------------------------------------------------------
# scale: cross-sectional scaling
# ---------------------------------------------------------------------------
@register_operator("scale")
def scale(df: pd.DataFrame, target: float = 1.0) -> pd.DataFrame:
    "Scale each row as x / sum(abs(x)) * target. The default target is 1."
    abs_sum = df.abs().sum(axis=1)
    abs_sum = abs_sum.replace(0, np.nan)
    return df.div(abs_sum, axis=0) * target


# ---------------------------------------------------------------------------
# demean: subtract the cross-sectional mean
# ---------------------------------------------------------------------------
@register_operator("demean")
def demean(df: pd.DataFrame) -> pd.DataFrame:
    "Subtract the cross-sectional mean from each observation."
    return df.sub(df.mean(axis=1), axis=0)


# ---------------------------------------------------------------------------
# winsorize: clip cross-sectional extremes
# ---------------------------------------------------------------------------
@register_operator("winsorize")
def winsorize(df: pd.DataFrame, lower: float = 0.025, upper: float = 0.975) -> pd.DataFrame:
    "Clip each row to its lower and upper quantiles. Defaults are the 2.5th and 97.5th percentiles."
    def _winsorize_row(row):
        q_low = row.quantile(lower)
        q_high = row.quantile(upper)
        return row.clip(q_low, q_high)

    return df.apply(_winsorize_row, axis=1)


# ---------------------------------------------------------------------------
# neutralize: remove group effects
# ---------------------------------------------------------------------------
@register_operator("neutralize")
def neutralize(df: pd.DataFrame, group_df: pd.DataFrame) -> pd.DataFrame:
    "Remove group effects by subtracting each group's cross-sectional mean. df and group_df are date-by-security matrices; group_df contains group labels such as industry codes."
    result = df.copy()
    for date in df.index:
        row = df.loc[date]
        groups = group_df.loc[date]
        group_mean = row.groupby(groups).transform("mean")
        result.loc[date] = row - group_mean
    return result
