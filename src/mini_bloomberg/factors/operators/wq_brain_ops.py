"Recovered BRAIN-style operator extensions: arithmetic, logical, time-series, cross-sectional, group, vector and reduction functions. Local behavior is not certified equivalent to BRAIN."

import pandas as pd
import numpy as np
from ..utils.registry import register_operator


# ===================================================================
# Additional arithmetic operators
# ===================================================================

@register_operator("add")
def add(df1, df2, filter_nan=False):
    "Elementwise addition. With filter_nan=True (expression alias filter), replace NaN inputs with zero."
    if filter_nan:
        return df1.fillna(0) + df2.fillna(0)
    return df1 + df2


@register_operator("subtract")
def subtract(df1, df2, filter_nan=False):
    "Elementwise subtraction. With filter_nan=True, replace NaN inputs with zero."
    if filter_nan:
        return df1.fillna(0) - df2.fillna(0)
    return df1 - df2


@register_operator("multiply")
def multiply(df1, df2, filter_nan=False):
    "Elementwise multiplication. With filter_nan=True, replace NaN inputs with one."
    if filter_nan:
        return df1.fillna(1) * df2.fillna(1)
    return df1 * df2


@register_operator("divide")
def divide(df1, df2):
    "Elementwise division x / y; zero denominators become NaN."
    return df1 / df2.replace(0, np.nan)


@register_operator("reverse")
def reverse(df):
    """-x"""
    return -df


def max_op(df1, df2):
    "Elementwise maximum of two inputs."
    return np.maximum(df1, df2)


def min_op(df1, df2):
    "Elementwise minimum of two inputs."
    return np.minimum(df1, df2)


@register_operator("densify")
def densify(df):
    "Map distinct group labels to consecutive integer codes. For example, {0, 1, 2, 99} becomes {0, 1, 2, 3}."
    def _densify_row(row):
        valid = row.dropna()
        if len(valid) == 0:
            return row
        codes, _ = pd.factorize(valid)
        result = row.copy()
        result[valid.index] = codes.astype(float)
        return result
    return df.apply(_densify_row, axis=1)


@register_operator("pasteurize")
def pasteurize(df):
    "Replace infinite values with NaN. This local implementation does not apply a platform universe mask."
    return df.replace([np.inf, -np.inf], np.nan)


# ===================================================================
# Logical operators
# ===================================================================

@register_operator("or")
def or_op(df1, df2):
    "Elementwise logical OR, returning 1 if either input is true and 0 otherwise."
    return (df1.astype(bool) | df2.astype(bool)).astype(float)


@register_operator("and")
def and_op(df1, df2):
    "Elementwise logical AND, returning 1 if both inputs are true and 0 otherwise."
    return (df1.astype(bool) & df2.astype(bool)).astype(float)


@register_operator("not")
def not_op(df):
    "Elementwise logical negation."
    return (~df.astype(bool)).astype(float)


@register_operator("is_nan")
def is_nan(df):
    "Return 1 where the input is NaN, and 0 elsewhere."
    return df.isna().astype(float)


@register_operator("less")
def less(df1, df2):
    """x < y"""
    return (df1 < df2).astype(float)


@register_operator("greater")
def greater(df1, df2):
    """x > y"""
    return (df1 > df2).astype(float)


@register_operator("equal")
def equal(df1, df2):
    """x == y"""
    return (df1 == df2).astype(float)


@register_operator("not_equal")
def not_equal(df1, df2):
    """x != y"""
    return (df1 != df2).astype(float)


@register_operator("less_equal")
def less_equal(df1, df2):
    """x <= y"""
    return (df1 <= df2).astype(float)


@register_operator("greater_equal")
def greater_equal(df1, df2):
    """x >= y"""
    return (df1 >= df2).astype(float)


# ===================================================================
# Additional time-series operators
# ===================================================================

@register_operator("ts_zscore")
def ts_zscore(df, d):
    "Time-series Z-score: (x - ts_mean(x, d)) / ts_std(x, d)."
    mean = df.rolling(d, min_periods=1).mean()
    std = df.rolling(d, min_periods=2).std()
    return (df - mean) / std.replace(0, np.nan)


@register_operator("ts_product")
def ts_product(df, d):
    "Product of observations within each rolling window."
    return df.rolling(d, min_periods=1).apply(np.prod, raw=True)


@register_operator("ts_ir")
def ts_ir(df, d):
    "Rolling information ratio: ts_mean(x, d) / ts_std(x, d)."
    mean = df.rolling(d, min_periods=1).mean()
    std = df.rolling(d, min_periods=2).std()
    return mean / std.replace(0, np.nan)


@register_operator("ts_av_diff")
def ts_av_diff(df, d):
    "Current value minus its rolling mean. Missing observations are ignored when calculating the mean."
    return df - df.rolling(d, min_periods=1).mean()


@register_operator("ts_max_diff")
def ts_max_diff(df, d):
    """ts_max_diff(x, d): x - ts_max(x, d)"""
    return df - df.rolling(d, min_periods=1).max()


@register_operator("ts_count_nans")
def ts_count_nans(df, d):
    "Count NaN observations within the rolling window."
    return df.isna().rolling(d, min_periods=1).sum()


@register_operator("ts_scale")
def ts_scale(df, d, constant=0):
    """ts_scale(x, d, constant=0): (x - ts_min) / (ts_max - ts_min) + constant"""
    ts_min = df.rolling(d, min_periods=1).min()
    ts_max = df.rolling(d, min_periods=1).max()
    rng = (ts_max - ts_min).replace(0, np.nan)
    return (df - ts_min) / rng + constant


@register_operator("ts_step")
def ts_step(df, step=1):
    "Observation counter starting at 1, multiplied by step. The expression engine supplies the context matrix automatically."
    if isinstance(df, pd.DataFrame):
        result = pd.DataFrame(index=df.index, columns=df.columns, dtype=float)
        for i, date in enumerate(df.index):
            result.loc[date] = (i + 1) * step
        return result
    return pd.Series(np.arange(1, len(df) + 1) * step, index=df.index)


@register_operator("ts_backfill")
def ts_backfill(df, lookback=252, k=1):
    "Fill missing observations using the kth most recent valid value in the trailing lookback window. k=1 selects the most recent valid value; k=2 selects the second most recent."
    def _backfill_col(series):
        result = series.copy()
        for i in range(len(series)):
            if pd.isna(series.iloc[i]):
                start = max(0, i - lookback)
                window = series.iloc[start:i]
                valid = window.dropna()
                if len(valid) >= k:
                    result.iloc[i] = valid.iloc[-k]
        return result
    return df.apply(_backfill_col)


@register_operator("days_from_last_change")
def days_from_last_change(df):
    "Number of observations since the value last changed."
    def _days_since(series):
        result = pd.Series(0, index=series.index, dtype=float)
        for i in range(1, len(series)):
            if series.iloc[i] == series.iloc[i - 1]:
                result.iloc[i] = result.iloc[i - 1] + 1
            else:
                result.iloc[i] = 0
        return result
    return df.apply(_days_since)


@register_operator("last_diff_value")
def last_diff_value(df, d):
    "Most recent value in the trailing d observations that differs from the current value."
    def _ldf_col(series):
        result = pd.Series(np.nan, index=series.index, dtype=float)
        for i in range(len(series)):
            curr = series.iloc[i]
            start = max(0, i - d)
            for j in range(i - 1, start - 1, -1):
                if not pd.isna(series.iloc[j]) and series.iloc[j] != curr:
                    result.iloc[i] = series.iloc[j]
                    break
        return result
    return df.apply(_ldf_col)


@register_operator("kth_element")
def kth_element(df, d, k=1, ignore="NaN"):
    "Return the kth valid observation in the rolling window; missing values are ignored according to the implementation."
    ignore_nan = "nan" in ignore.lower()
    ignore_zero = "0" in ignore

    def _kth_col(series):
        result = pd.Series(np.nan, index=series.index, dtype=float)
        for i in range(len(series)):
            start = max(0, i - d + 1)
            window = series.iloc[start:i + 1]
            valid = window.copy()
            if ignore_nan:
                valid = valid.dropna()
            if ignore_zero:
                valid = valid[valid != 0]
            if len(valid) >= k:
                result.iloc[i] = valid.iloc[-k]
        return result
    return df.apply(_kth_col)


@register_operator("hump")
def hump(df, hump_val=0.01):
    "Limit daily changes to reduce turnover. Small changes retain the previous value; larger changes advance by the calculated limit. This local implementation derives the limit from hump_val and the mean."
    def _hump_col(series):
        result = series.copy()
        limit = hump_val * series.abs().mean()  # Simplification: limit is hump times the mean
        if pd.isna(limit) or limit == 0:
            return result
        for i in range(1, len(series)):
            if pd.isna(series.iloc[i]) or pd.isna(result.iloc[i - 1]):
                continue
            diff = series.iloc[i] - result.iloc[i - 1]
            if abs(diff) <= limit:
                result.iloc[i] = result.iloc[i - 1]
            else:
                result.iloc[i] = result.iloc[i - 1] + np.sign(diff) * limit
        return result
    return df.apply(_hump_col)


@register_operator("ts_regression")
def ts_regression(y, x, d, lag=0, rettype=0):
    "Rolling ordinary least squares regression of y on lagged x over d observations. rettype: 0=residual, 1=intercept, 2=slope, 3=fitted y, 4=SSE, 5=SST, 6=R-squared."
    def _regress_col(y_col, x_col):
        result = pd.Series(np.nan, index=y_col.index, dtype=float)
        x_lagged = x_col.shift(lag) if lag > 0 else x_col

        for i in range(d - 1, len(y_col)):
            yy = y_col.iloc[i - d + 1:i + 1]
            xx = x_lagged.iloc[i - d + 1:i + 1]
            mask = yy.notna() & xx.notna()
            if mask.sum() < 3:
                continue

            yv = yy[mask].values.astype(float)
            xv = xx[mask].values.astype(float)
            n = len(yv)

            # OLS
            x_mean = xv.mean()
            y_mean = yv.mean()
            ss_xy = ((xv - x_mean) * (yv - y_mean)).sum()
            ss_xx = ((xv - x_mean) ** 2).sum()

            if ss_xx == 0:
                continue

            beta = ss_xy / ss_xx
            alpha_coef = y_mean - beta * x_mean
            y_hat = alpha_coef + beta * xv
            residuals = yv - y_hat

            if rettype == 0:
                result.iloc[i] = residuals[-1]
            elif rettype == 1:
                result.iloc[i] = alpha_coef
            elif rettype == 2:
                result.iloc[i] = beta
            elif rettype == 3:
                result.iloc[i] = y_hat[-1]
            elif rettype == 4:
                result.iloc[i] = (residuals ** 2).sum()
            elif rettype == 5:
                result.iloc[i] = ((yv - y_mean) ** 2).sum()
            elif rettype == 6:
                sst = ((yv - y_mean) ** 2).sum()
                sse = (residuals ** 2).sum()
                result.iloc[i] = 1 - sse / sst if sst > 0 else np.nan

        return result

    if isinstance(y, pd.DataFrame) and isinstance(x, pd.DataFrame):
        result = pd.DataFrame(index=y.index, columns=y.columns, dtype=float)
        for col in y.columns:
            if col in x.columns:
                result[col] = _regress_col(y[col], x[col])
        return result
    return _regress_col(y, x)


@register_operator("ts_quantile")
def ts_quantile(df, d, driver="gaussian"):
    "Map rolling percentile ranks through an inverse distribution transform. Supported drivers: gaussian, uniform and cauchy."
    from statistics import NormalDist
    normal_ppf = np.vectorize(lambda p: NormalDist().inv_cdf(p) if np.isfinite(p) else np.nan)

    def _rolling_rank(series):
        return series.rolling(d, min_periods=1).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
        )

    ranked = df.apply(_rolling_rank)
    # Clip endpoints to avoid infinite inverse-CDF values
    eps = 1e-6
    ranked = ranked.clip(eps, 1 - eps)

    if driver == "gaussian":
        return ranked.apply(normal_ppf)
    elif driver == "cauchy":
        return np.tan(np.pi * (ranked - 0.5))
    elif driver == "uniform":
        return ranked - ranked.mean(axis=1).values[:, None]
    return ranked


# ===================================================================
# Additional cross-sectional operators
# ===================================================================

@register_operator("normalize")
def normalize(df, useStd=False, limit=0.0):
    "Subtract the cross-sectional mean; optionally divide by the standard deviation with useStd and clip with limit."
    mean = df.mean(axis=1)
    result = df.sub(mean, axis=0)
    if useStd:
        std = result.std(axis=1).replace(0, np.nan)
        result = result.div(std, axis=0)
    if limit > 0:
        result = result.clip(-limit, limit)
    return result


@register_operator("quantile_cs")
def quantile_cs(df, driver="gaussian", sigma=1.0):
    "Transform cross-sectional ranks using a shift and inverse distribution mapping. Supported drivers: gaussian, uniform and cauchy; sigma scales the output."
    from statistics import NormalDist
    normal_ppf = np.vectorize(lambda p: NormalDist().inv_cdf(p) if np.isfinite(p) else np.nan)

    ranked = df.rank(axis=1, pct=True)
    n = df.notna().sum(axis=1)
    # shift: rank -> [1/N, 1-1/N]
    shifted = ranked.mul(1 - 2.0 / n, axis=0).add(1.0 / n, axis=0)
    shifted = shifted.clip(1e-6, 1 - 1e-6)

    if driver == "gaussian":
        return shifted.apply(lambda x: normal_ppf(x) * sigma)
    elif driver == "cauchy":
        return shifted.apply(lambda x: np.tan(np.pi * (x - 0.5)) * sigma)
    elif driver == "uniform":
        return shifted.sub(shifted.mean(axis=1), axis=0) * sigma
    return shifted


# ===================================================================
# Additional transformations
# ===================================================================

@register_operator("tail")
def tail(df, lower=0, upper=0, newval=0):
    "Replace x with newval where lower < x < upper; keep x elsewhere."
    mask = (df > lower) & (df < upper)
    return df.where(~mask, newval)


@register_operator("trade_when")
def trade_when(trigger, alpha_val, exit_cond):
    "Update the stored alpha when trigger > 0, exit to NaN when exit_cond > 0, otherwise retain the previous alpha. Exit takes priority; the initial holding is NaN."
    result = pd.DataFrame(np.nan, index=alpha_val.index, columns=alpha_val.columns)
    def mask(value):
        if np.isscalar(value):
            return pd.DataFrame(value > 0, index=result.index, columns=result.columns)
        return value.gt(0).fillna(False)
    entry, leave = mask(trigger), mask(exit_cond)
    previous = pd.Series(np.nan, index=result.columns)
    for i in range(len(result)):
        previous = previous.where(~entry.iloc[i], alpha_val.iloc[i]).where(~leave.iloc[i])
        result.iloc[i] = previous
    return result


@register_operator("bucket")
def bucket(df, range_str=None, buckets_str=None):
    "Discretize values into bucket indices. Use range_str (expression alias range), e.g. \"0,1,0.1\", or buckets_str (alias buckets), e.g. \"0.2,0.5,0.7\"."
    if range_str:
        parts = [float(x.strip()) for x in range_str.split(",")]
        start, end, step = parts[0], parts[1], parts[2]
        bins = np.arange(start, end + step, step)
    elif buckets_str:
        bins = [-np.inf] + [float(x.strip()) for x in buckets_str.split(",")] + [np.inf]
    else:
        bins = np.linspace(0, 1, 11)

    def _bucket_row(row):
        return pd.cut(row, bins=bins, labels=False, include_lowest=True)

    return df.apply(_bucket_row, axis=1).astype(float)


# ===================================================================
# Additional group operators
# ===================================================================

@register_operator("group_sum")
def group_sum(df, group_df):
    "Sum values within each group and date."
    result = pd.DataFrame(index=df.index, columns=df.columns, dtype=float)
    for date in df.index:
        row = df.loc[date]
        groups = group_df.loc[date]
        valid = row.notna() & groups.notna()
        if valid.sum() == 0:
            continue
        transformed = row[valid].groupby(groups[valid]).transform("sum")
        result.loc[date, valid] = transformed.values
    return result


@register_operator("group_std_dev")
def group_std_dev(df, group_df):
    "Standard deviation within each group and date."
    result = pd.DataFrame(index=df.index, columns=df.columns, dtype=float)
    for date in df.index:
        row = df.loc[date]
        groups = group_df.loc[date]
        valid = row.notna() & groups.notna()
        if valid.sum() == 0:
            continue
        transformed = row[valid].groupby(groups[valid]).transform("std")
        result.loc[date, valid] = transformed.values
    return result


@register_operator("group_count")
def group_count(df, group_df):
    "Count valid values within each group and date."
    result = pd.DataFrame(index=df.index, columns=df.columns, dtype=float)
    for date in df.index:
        row = df.loc[date]
        groups = group_df.loc[date]
        valid = row.notna() & groups.notna()
        if valid.sum() == 0:
            continue
        transformed = row[valid].groupby(groups[valid]).transform("count")
        result.loc[date, valid] = transformed.values
    return result


@register_operator("group_scale")
def group_scale(df, group_df):
    "Min-max scaling to [0, 1] within each group and date."
    def _scale(x):
        rng = x.max() - x.min()
        if rng == 0 or pd.isna(rng):
            return x * 0 + 0.5
        return (x - x.min()) / rng

    result = pd.DataFrame(index=df.index, columns=df.columns, dtype=float)
    for date in df.index:
        row = df.loc[date]
        groups = group_df.loc[date]
        valid = row.notna() & groups.notna()
        if valid.sum() == 0:
            continue
        transformed = row[valid].groupby(groups[valid]).transform(_scale)
        result.loc[date, valid] = transformed.values
    return result


@register_operator("group_cartesian_product")
def group_cartesian_product(g1, g2):
    "Combine two group labels using g1 * 1000 + g2. Example: 2 and 3 become 2003. This encoding can collide for unrestricted label ranges."
    max_g2 = g2.max().max() + 1 if g2.notna().any().any() else 1000
    return g1 * max_g2 + g2


# ===================================================================
# Vector operators (local emulation using apply)
# ===================================================================

@register_operator("vec_sum")
def vec_sum(df):
    "Sum vector elements. The local DataFrame implementation operates across columns."
    if isinstance(df, pd.DataFrame):
        return df.sum(axis=1)
    return df.apply(lambda x: np.nansum(x) if hasattr(x, '__iter__') else x)


@register_operator("vec_avg")
def vec_avg(df):
    "Mean of vector elements. The local DataFrame implementation operates across columns."
    if isinstance(df, pd.DataFrame):
        return df.mean(axis=1)
    return df.apply(lambda x: np.nanmean(x) if hasattr(x, '__iter__') else x)


@register_operator("vec_max")
def vec_max(df):
    "Maximum vector element. The local DataFrame implementation operates across columns."
    if isinstance(df, pd.DataFrame):
        return df.max(axis=1)
    return df.apply(lambda x: np.nanmax(x) if hasattr(x, '__iter__') else x)


@register_operator("vec_min")
def vec_min(df):
    "Minimum vector element. The local DataFrame implementation operates across columns."
    if isinstance(df, pd.DataFrame):
        return df.min(axis=1)
    return df.apply(lambda x: np.nanmin(x) if hasattr(x, '__iter__') else x)


@register_operator("vec_count")
def vec_count(df):
    "Count non-NaN vector elements. The local DataFrame implementation operates across columns."
    if isinstance(df, pd.DataFrame):
        return df.notna().sum(axis=1)
    return df.apply(lambda x: np.sum(~np.isnan(x)) if hasattr(x, '__iter__') else 1)


@register_operator("vec_stddev")
def vec_stddev(df):
    "Standard deviation of vector elements. The local DataFrame implementation operates across columns."
    if isinstance(df, pd.DataFrame):
        return df.std(axis=1)
    return df.apply(lambda x: np.nanstd(x) if hasattr(x, '__iter__') else 0)


@register_operator("vec_range")
def vec_range(df):
    "Vector range: maximum minus minimum. The local DataFrame implementation operates across columns."
    if isinstance(df, pd.DataFrame):
        return df.max(axis=1) - df.min(axis=1)
    return df.apply(lambda x: np.nanmax(x) - np.nanmin(x) if hasattr(x, '__iter__') else 0)


# ===================================================================
# Reduction operators acting across the last matrix dimension
# ===================================================================

@register_operator("reduce_avg")
def reduce_avg(df, threshold=0):
    "Mean across the last dimension. threshold specifies the minimum valid-observation count."
    count = df.notna().sum(axis=1)
    result = df.mean(axis=1)
    if threshold > 0:
        result = result.where(count >= threshold)
    return result


@register_operator("reduce_sum")
def reduce_sum(df):
    "Sum across the last dimension."
    return df.sum(axis=1)


@register_operator("reduce_max")
def reduce_max(df):
    "Maximum across the last dimension."
    return df.max(axis=1)


@register_operator("reduce_min")
def reduce_min(df):
    "Minimum across the last dimension."
    return df.min(axis=1)


@register_operator("reduce_norm")
def reduce_norm(df):
    "Sum of absolute values across the last dimension."
    return df.abs().sum(axis=1)


@register_operator("reduce_range")
def reduce_range(df):
    "Maximum minus minimum across the last dimension."
    return df.max(axis=1) - df.min(axis=1)


@register_operator("reduce_stddev")
def reduce_stddev(df, threshold=0):
    "Standard deviation across the last dimension."
    count = df.notna().sum(axis=1)
    result = df.std(axis=1)
    if threshold > 0:
        result = result.where(count >= threshold)
    return result


@register_operator("reduce_ir")
def reduce_ir(df):
    """reduce_ir: IR = mean / std"""
    mean = df.mean(axis=1)
    std = df.std(axis=1).replace(0, np.nan)
    return mean / std


@register_operator("reduce_skewness")
def reduce_skewness(df):
    "Skewness across the last dimension."
    return df.skew(axis=1)


@register_operator("reduce_kurtosis")
def reduce_kurtosis(df):
    "Kurtosis across the last dimension."
    return df.kurtosis(axis=1)


@register_operator("reduce_count")
def reduce_count(df, threshold=0):
    "Count values greater than threshold across the last dimension."
    return (df > threshold).sum(axis=1)


@register_operator("reduce_powersum")
def reduce_powersum(df, constant=2):
    """reduce_powersum: sum(|x|^constant)"""
    return df.abs().pow(constant).sum(axis=1)


@register_operator("reduce_percentage")
def reduce_percentage(df, percentage=0.5):
    "Quantile at percentage across the last dimension."
    return df.quantile(percentage, axis=1)


@register_operator("reduce_choose")
def reduce_choose(df, nth=1, ignoreNan=True):
    "Select the nth element across the last dimension."
    def _choose(row):
        if ignoreNan:
            valid = row.dropna()
        else:
            valid = row
        if len(valid) >= nth:
            return valid.iloc[nth - 1]
        return np.nan
    return df.apply(_choose, axis=1)
