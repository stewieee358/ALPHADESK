"Factor evaluation: cross-sectional IC and Rank IC, quantile returns, turnover and IC decay. Matrices use dates as rows and securities as columns."

import pandas as pd
import numpy as np
from typing import Optional, Dict


class FactorEvaluator:
    "Evaluate factor predictiveness, quantile returns and portfolio turnover."

    def __init__(
        self,
        factor: pd.DataFrame,
        returns: pd.DataFrame,
        n_groups: int = 5,
        holding_period: int = 1,
    ):
        "Initialize evaluation with factor and unshifted daily-return matrices. Rows are dates, columns are securities. n_groups sets the quantile count; holding_period sets the forward return horizon."
        # Align dates and security columns
        common_dates = factor.index.intersection(returns.index)
        common_stocks = factor.columns.intersection(returns.columns)
        self.factor = factor.loc[common_dates, common_stocks]
        self.returns = returns.loc[common_dates, common_stocks]
        self.n_groups = n_groups
        self.holding_period = holding_period

        # Align forward returns with the signal date and holding period
        forward = (1 + returns).rolling(holding_period, min_periods=holding_period).apply(np.prod, raw=True).shift(-holding_period) - 1
        self.forward_returns = forward.reindex(index=common_dates, columns=common_stocks)

    # -------------------------------------------------------------------
    # IC calculations
    # -------------------------------------------------------------------

    def calc_ic(self) -> pd.Series:
        "Daily cross-sectional Pearson correlation between the factor and forward returns. Requires at least 10 valid pairs per date."
        ic_series = []
        for date in self.factor.index:
            f = self.factor.loc[date].dropna()
            r = self.forward_returns.loc[date].dropna()
            common = f.index.intersection(r.index)
            if len(common) < 10:
                ic_series.append(np.nan)
                continue
            ic = f[common].corr(r[common])
            ic_series.append(ic)
        return pd.Series(ic_series, index=self.factor.index, name="IC")

    def calc_rank_ic(self) -> pd.Series:
        "Daily cross-sectional rank correlation between the factor and forward returns. Requires at least 10 valid pairs per date."
        rank_factor = self.factor.rank(axis=1, pct=True)
        rank_returns = self.forward_returns.rank(axis=1, pct=True)

        ic_series = []
        for date in rank_factor.index:
            f = rank_factor.loc[date].dropna()
            r = rank_returns.loc[date].dropna()
            common = f.index.intersection(r.index)
            if len(common) < 10:
                ic_series.append(np.nan)
                continue
            ic = f[common].rank().corr(r[common].rank())
            ic_series.append(ic)
        return pd.Series(ic_series, index=self.factor.index, name="RankIC")

    def ic_summary(self) -> Dict[str, float]:
        "Summarize IC and Rank IC means, standard deviations, information ratios and the positive-IC fraction."
        ic = self.calc_ic().dropna()
        rank_ic = self.calc_rank_ic().dropna()
        return {
            "IC_mean":     ic.mean(),
            "IC_std":      ic.std(),
            "IR":          ic.mean() / ic.std() if ic.std() > 0 else 0,
            "IC_positive": (ic > 0).mean(),  # Fraction of positive IC observations
            "RankIC_mean": rank_ic.mean(),
            "RankIC_std":  rank_ic.std(),
            "RankIR":      rank_ic.mean() / rank_ic.std() if rank_ic.std() > 0 else 0,
        }

    # -------------------------------------------------------------------
    # Quantile portfolio returns
    # -------------------------------------------------------------------

    def layered_returns(self) -> pd.DataFrame:
        "Assign factor observations to n_groups quantiles and calculate each group's mean forward return. Columns Q1 through Qn represent ascending factor groups; L-S is Qn minus Q1."
        group_returns = pd.DataFrame(index=self.factor.index)

        for date in self.factor.index:
            f = self.factor.loc[date].dropna()
            r = self.forward_returns.loc[date].dropna()
            common = f.index.intersection(r.index)

            if len(common) < self.n_groups * 2:
                continue

            f_aligned = f[common]
            r_aligned = r[common]

            # Group observations by factor value
            try:
                groups = pd.qcut(f_aligned, self.n_groups, labels=False, duplicates="drop")
            except ValueError:
                continue

            for g in range(self.n_groups):
                mask = groups == g
                group_name = f"Q{g + 1}"
                if mask.sum() > 0:
                    group_returns.loc[date, group_name] = r_aligned[mask].mean()

        # Long-short returns
        if f"Q{self.n_groups}" in group_returns.columns and "Q1" in group_returns.columns:
            group_returns["L-S"] = (
                group_returns[f"Q{self.n_groups}"] - group_returns["Q1"]
            )

        return group_returns.astype(float)

    def cumulative_layered_returns(self) -> pd.DataFrame:
        "Compound daily quantile returns into cumulative portfolio values. Overlapping multi-day returns cannot be compounded directly."
        if self.holding_period != 1:
            raise ValueError("Cumulative curves require holding_period=1; multi-day returns overlap")
        lr = self.layered_returns()
        return (1 + lr.fillna(0)).cumprod()

    # -------------------------------------------------------------------
    # Turnover
    # -------------------------------------------------------------------

    def calc_turnover(self, top_pct: float = 0.2) -> pd.Series:
        "Estimate turnover from changes in the highest-ranked top_pct holdings. Uses the symmetric set difference divided by twice the current holding count; the first observation is missing."
        factor_rank = self.factor.rank(axis=1, pct=True)
        holdings = factor_rank >= (1 - top_pct)  # Select the highest-ranked top_pct holdings

        turnover_list = []
        prev_hold = None
        for date in holdings.index:
            curr_hold = set(holdings.columns[holdings.loc[date]])
            if prev_hold is not None and len(curr_hold) > 0:
                changed = len(curr_hold.symmetric_difference(prev_hold))
                turnover = changed / (2 * max(len(curr_hold), 1))
                turnover_list.append(turnover)
            else:
                turnover_list.append(np.nan)
            prev_hold = curr_hold

        return pd.Series(turnover_list, index=holdings.index, name="turnover")

    # -------------------------------------------------------------------
    # IC decay
    # -------------------------------------------------------------------

    def ic_decay(self, max_lag: int = 20) -> pd.Series:
        "Measure mean cross-sectional IC between the factor at T and the single-day return at T+lag, for lags 1 through max_lag."
        decay = {}
        for lag in range(1, max_lag + 1):
            fwd = self.returns.shift(-lag)
            ic_list = []
            for date in self.factor.index:
                f = self.factor.loc[date].dropna()
                r = fwd.loc[date].dropna() if date in fwd.index else pd.Series(dtype=float)
                common = f.index.intersection(r.index)
                if len(common) >= 10:
                    ic_list.append(f[common].corr(r[common]))
            decay[lag] = np.nanmean(ic_list) if ic_list else np.nan
        return pd.Series(decay, name="IC_decay")

    # -------------------------------------------------------------------
    # Summary report
    # -------------------------------------------------------------------

    def full_report(self) -> str:
        "Return a formatted report of IC statistics, turnover and IC decay."
        ic_stats = self.ic_summary()
        turnover = self.calc_turnover()
        decay = self.ic_decay(max_lag=10)

        lines = [
            "=" * 50,
            "Factor Evaluation Report",
            "=" * 50,
            "",
            "--- IC Analysis ---",
            f"  IC Mean:         {ic_stats['IC_mean']:.4f}",
            f"  IC Std:          {ic_stats['IC_std']:.4f}",
            f"  IR:              {ic_stats['IR']:.4f}",
            f"  IC > 0 Ratio:    {ic_stats['IC_positive']:.2%}",
            f"  Rank IC Mean:    {ic_stats['RankIC_mean']:.4f}",
            f"  Rank IR:         {ic_stats['RankIR']:.4f}",
            "",
            "--- Turnover ---",
            f"  Mean Turnover:   {turnover.mean():.4f}",
            f"  Turnover Std:    {turnover.std():.4f}",
            "",
            "--- IC Decay ---",
        ]
        for lag, ic_val in decay.items():
            bar = "█" * max(1, int(abs(ic_val) * 100)) if not np.isnan(ic_val) else ""
            lines.append(f"  Lag {lag:2d}: {ic_val:+.4f}  {bar}")

        lines.append("")
        lines.append("=" * 50)
        return "\n".join(lines)
