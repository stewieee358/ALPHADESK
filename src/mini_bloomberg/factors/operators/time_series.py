"Rolling time-series operators apply independently to each security along the date index."

import pandas as pd
import numpy as np
from ..utils.registry import register_operator


# ---------------------------------------------------------------------------
# Basic rolling windows
# ---------------------------------------------------------------------------

@register_operator("ts_mean")
def ts_mean(df: pd.DataFrame, d: int) -> pd.DataFrame:
    "Rolling mean over the previous d observations, independently for each security."
    return df.rolling(window=d, min_periods=1).mean()


@register_operator("ts_sum")
def ts_sum(df: pd.DataFrame, d: int) -> pd.DataFrame:
    "Rolling sum over the previous d observations."
    return df.rolling(window=d, min_periods=1).sum()


@register_operator("ts_std")
def ts_std(df: pd.DataFrame, d: int) -> pd.DataFrame:
    "Rolling standard deviation over the previous d observations."
    return df.rolling(window=d, min_periods=2).std()


@register_operator("ts_min")
def ts_min(df: pd.DataFrame, d: int) -> pd.DataFrame:
    "Rolling minimum over the previous d observations."
    return df.rolling(window=d, min_periods=1).min()


@register_operator("ts_max")
def ts_max(df: pd.DataFrame, d: int) -> pd.DataFrame:
    "Rolling maximum over the previous d observations."
    return df.rolling(window=d, min_periods=1).max()


@register_operator("ts_skew")
def ts_skew(df: pd.DataFrame, d: int) -> pd.DataFrame:
    "Rolling skewness over the previous d observations."
    return df.rolling(window=d, min_periods=3).skew()


@register_operator("ts_kurt")
def ts_kurt(df: pd.DataFrame, d: int) -> pd.DataFrame:
    "Rolling kurtosis over the previous d observations."
    return df.rolling(window=d, min_periods=4).kurt()


# ---------------------------------------------------------------------------
# Ranks and extreme-value positions
# ---------------------------------------------------------------------------

@register_operator("ts_rank")
def ts_rank(df: pd.DataFrame, d: int) -> pd.DataFrame:
    "Percentile rank of the current observation within the trailing d-observation window."
    def _rolling_rank(series):
        return series.rolling(window=d, min_periods=1).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1],
            raw=False
        )
    return df.apply(_rolling_rank)


@register_operator("ts_argmax")
def ts_argmax(df: pd.DataFrame, d: int) -> pd.DataFrame:
    "Distance in observations to the maximum within the rolling window: 0 indicates the current observation and d-1 the oldest observation in a full window."
    def _rolling_argmax(series):
        return series.rolling(window=d, min_periods=1).apply(
            lambda x: (d - 1) - np.argmax(x), raw=True
        )
    return df.apply(_rolling_argmax)


@register_operator("ts_argmin")
def ts_argmin(df: pd.DataFrame, d: int) -> pd.DataFrame:
    "Distance in observations to the minimum within the rolling window."
    def _rolling_argmin(series):
        return series.rolling(window=d, min_periods=1).apply(
            lambda x: (d - 1) - np.argmin(x), raw=True
        )
    return df.apply(_rolling_argmin)


# ---------------------------------------------------------------------------
# Two-series operators
# ---------------------------------------------------------------------------

@register_operator("ts_corr")
def ts_corr(df1: pd.DataFrame, df2: pd.DataFrame, d: int) -> pd.DataFrame:
    "Rolling Pearson correlation between two series over d observations. Example: ts_corr(close, volume, 20)."
    result = {}
    for col in df1.columns:
        if col in df2.columns:
            result[col] = df1[col].rolling(window=d, min_periods=2).corr(df2[col])
    return pd.DataFrame(result, index=df1.index)


@register_operator("ts_cov")
def ts_cov(df1: pd.DataFrame, df2: pd.DataFrame, d: int) -> pd.DataFrame:
    "Rolling covariance between two series over d observations."
    result = {}
    for col in df1.columns:
        if col in df2.columns:
            result[col] = df1[col].rolling(window=d, min_periods=2).cov(df2[col])
    return pd.DataFrame(result, index=df1.index)


# ---------------------------------------------------------------------------
# Differences and lags
# ---------------------------------------------------------------------------

@register_operator("delta")
def delta(df: pd.DataFrame, d: int = 1) -> pd.DataFrame:
    "Difference x(t) - x(t-d)."
    return df.diff(periods=d)


@register_operator("delay")
def delay(df: pd.DataFrame, d: int = 1) -> pd.DataFrame:
    "Lag the input by d observations: x(t-d)."
    return df.shift(periods=d)


@register_operator("ts_returns")
def ts_returns(df: pd.DataFrame, d: int = 1) -> pd.DataFrame:
    "Relative change over d observations: x(t) / x(t-d) - 1."
    return df.pct_change(periods=d)


# ---------------------------------------------------------------------------
# Decay weighting
# ---------------------------------------------------------------------------

@register_operator("decay_linear")
def decay_linear(df: pd.DataFrame, d: int) -> pd.DataFrame:
    "Linearly weighted rolling mean. Weights increase from 1 for the oldest observation to d for the most recent, then are normalized to sum to one."
    weights = np.arange(1, d + 1, dtype=float)
    weights = weights / weights.sum()

    def _weighted_mean(series):
        return series.rolling(window=d, min_periods=d).apply(
            lambda x: np.dot(x, weights), raw=True
        )
    return df.apply(_weighted_mean)


@register_operator("decay_exp")
def decay_exp(df: pd.DataFrame, d: int, factor: float = 0.5) -> pd.DataFrame:
    "Exponentially weighted rolling mean, using weights factor**(d-1) through factor**0 from oldest to newest."
    weights = np.array([factor ** i for i in range(d - 1, -1, -1)])
    weights = weights / weights.sum()

    def _exp_mean(series):
        return series.rolling(window=d, min_periods=d).apply(
            lambda x: np.dot(x, weights), raw=True
        )
    return df.apply(_exp_mean)
