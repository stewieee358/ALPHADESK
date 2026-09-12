"Elementwise mathematical transforms and conditional selection for factor matrices."

import pandas as pd
import numpy as np
from ..utils.registry import register_operator


@register_operator("log")
def log_op(df: pd.DataFrame) -> pd.DataFrame:
    "Natural logarithm ln(x). Nonpositive values become NaN."
    return np.log(df.where(df > 0))


@register_operator("log1p")
def log1p_op(df: pd.DataFrame) -> pd.DataFrame:
    "Compute ln(1 + x), with improved numerical stability near zero."
    return np.log1p(df)


@register_operator("abs")
def abs_op(df: pd.DataFrame) -> pd.DataFrame:
    "Elementwise absolute value abs(x)."
    return df.abs()


@register_operator("sign")
def sign_op(df: pd.DataFrame) -> pd.DataFrame:
    "Elementwise sign: 1 for positive values, -1 for negative values and 0 for zero."
    return np.sign(df)


@register_operator("power")
def power(df: pd.DataFrame, exp: float) -> pd.DataFrame:
    "Elementwise power x ** exp."
    return df.pow(exp)


@register_operator("signed_power")
def signed_power(df: pd.DataFrame, exp: float) -> pd.DataFrame:
    "Signed power: sign(x) * abs(x) ** exp. Preserves the original sign."
    return np.sign(df) * df.abs().pow(exp)


@register_operator("sigmoid")
def sigmoid(df: pd.DataFrame) -> pd.DataFrame:
    "Logistic transform 1 / (1 + exp(-x)), mapping finite inputs to (0, 1)."
    return 1.0 / (1.0 + np.exp(-df))


@register_operator("tanh")
def tanh_op(df: pd.DataFrame) -> pd.DataFrame:
    "Hyperbolic tangent, mapping finite inputs to (-1, 1)."
    return np.tanh(df)


@register_operator("clip")
def clip_op(df: pd.DataFrame, lower: float = None, upper: float = None) -> pd.DataFrame:
    "Clip values to the interval [lower, upper]."
    return df.clip(lower=lower, upper=upper)


@register_operator("max_of")
def max_op(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    "Elementwise maximum of two inputs."
    return np.maximum(df1, df2)


@register_operator("min_of")
def min_op(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    "Elementwise minimum of two inputs."
    return np.minimum(df1, df2)


@register_operator("if_else")
def if_else(cond: pd.DataFrame, true_val: pd.DataFrame, false_val: pd.DataFrame) -> pd.DataFrame:
    "Select true_val where cond is true or nonzero, and false_val elsewhere. Missing conditions are treated as false."
    return pd.DataFrame(np.where(cond.fillna(False).astype(bool), true_val, false_val), index=cond.index, columns=cond.columns)


@register_operator("inv")
def inv(df: pd.DataFrame) -> pd.DataFrame:
    "Reciprocal 1 / x. Zero denominators become NaN."
    return 1.0 / df.replace(0, np.nan)


@register_operator("sqrt")
def sqrt_op(df: pd.DataFrame) -> pd.DataFrame:
    "Square root; negative values become NaN."
    return np.sqrt(df.where(df >= 0))
