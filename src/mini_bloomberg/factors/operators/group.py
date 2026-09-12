"Group operators partition each date by group labels and calculate within-group statistics."

import pandas as pd
import numpy as np
from ..utils.registry import register_operator


def _apply_group_func(df: pd.DataFrame, group_df: pd.DataFrame, func) -> pd.DataFrame:
    "For each date, partition observations by group_df and apply func to each group. func receives a Series of group values and returns a Series."
    result = pd.DataFrame(index=df.index, columns=df.columns, dtype=float)

    for date in df.index:
        row = df.loc[date]
        groups = group_df.loc[date]

        # Skip rows containing only NaN values
        valid_mask = row.notna() & groups.notna()
        if valid_mask.sum() == 0:
            continue

        row_valid = row[valid_mask]
        groups_valid = groups[valid_mask]

        transformed = row_valid.groupby(groups_valid).transform(func)
        result.loc[date, valid_mask] = transformed.values

    return result


@register_operator("group_rank")
def group_rank(df: pd.DataFrame, group_df: pd.DataFrame) -> pd.DataFrame:
    "Percentile rank within each group and date. Example: group_rank(momentum, industry)."
    return _apply_group_func(df, group_df, lambda x: x.rank(pct=True))


@register_operator("group_zscore")
def group_zscore(df: pd.DataFrame, group_df: pd.DataFrame) -> pd.DataFrame:
    "Standardize values within each group and date using the group mean and standard deviation."
    def _zscore(x):
        std = x.std()
        if std == 0 or pd.isna(std):
            return x * 0
        return (x - x.mean()) / std

    return _apply_group_func(df, group_df, _zscore)


@register_operator("group_demean")
def group_demean(df: pd.DataFrame, group_df: pd.DataFrame) -> pd.DataFrame:
    "Subtract the group mean: x - group_mean(x)."
    return _apply_group_func(df, group_df, lambda x: x - x.mean())


@register_operator("group_mean")
def group_mean(df: pd.DataFrame, group_df: pd.DataFrame) -> pd.DataFrame:
    "Replace each observation with the mean of its group on that date."
    return _apply_group_func(df, group_df, lambda x: pd.Series(x.mean(), index=x.index))


@register_operator("ind_neutralize")
def ind_neutralize(df: pd.DataFrame, industry_df: pd.DataFrame) -> pd.DataFrame:
    "Industry-neutralization alias of group_demean; industry_df supplies the group labels."
    return group_demean(df, industry_df)
