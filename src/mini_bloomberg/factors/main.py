"Example factor calculation and evaluation using synthetic data. Run as python -m mini_bloomberg.factors.main. Replace the synthetic inputs with a DataLoader for market research."

import sys
sys.path.insert(0, "/home/claude")

import numpy as np
import pandas as pd

# ===========================================================================
# 1. Import the framework
# ===========================================================================
from mini_bloomberg.factors import (
    Context, ExpressionEngine, DataLoader, FactorEvaluator, list_operators
)

print("=" * 60)
print("Quant Factor Mining Engine - Demo")
print("=" * 60)

# Inspect all registered operators
ops = list_operators()
print(f"\nRegistered {len(ops)} operators:")
for name in sorted(ops.keys()):
    print(f"  - {name}")

# ===========================================================================
# 2. Generate synthetic data (replace with market data for research)
# ===========================================================================
print("\n--- Generating synthetic data ---")

np.random.seed(42)
n_dates = 500
n_stocks = 50

dates = pd.bdate_range("2022-01-01", periods=n_dates)
stocks = [f"{i:06d}.SZ" for i in range(1, n_stocks + 1)]

# Simulate price changes with trend and noise
close = pd.DataFrame(
    np.cumsum(np.random.randn(n_dates, n_stocks) * 0.02, axis=0) + 4,
    index=dates, columns=stocks
)
close = np.exp(close)  # Convert changes into prices

open_price = close * (1 + np.random.randn(n_dates, n_stocks) * 0.005)
high = np.maximum(close, open_price) * (1 + np.abs(np.random.randn(n_dates, n_stocks)) * 0.01)
low = np.minimum(close, open_price) * (1 - np.abs(np.random.randn(n_dates, n_stocks)) * 0.01)
volume = pd.DataFrame(
    np.random.lognormal(15, 1, (n_dates, n_stocks)),
    index=dates, columns=stocks
)

# ===========================================================================
# 3. Create the context and load data
# ===========================================================================
ctx = DataLoader.from_dataframe({
    "close": close,
    "open": open_price,
    "high": high,
    "low": low,
    "volume": volume,
})
print(ctx)

# ===========================================================================
# 4. Evaluate factor expressions
# ===========================================================================
print("\n--- Factor calculation ---")
engine = ExpressionEngine(ctx)

# Define a batch of factors
factors = {
    "momentum_20d":      "ts_returns(close, 20)",
    "vol_rank":          "rank(ts_std(close, 20))",
    "mean_reversion":    "-1 * rank(close / ts_mean(close, 20))",
    "volume_surprise":   "rank(volume / ts_mean(volume, 20))",
    "price_range":       "rank((high - low) / close)",
    "alpha001":          "rank(ts_argmax(close ** 2, 5))",
}

results = engine.batch_evaluate(factors)

for name, df in results.items():
    if df is not None:
        print(f"  [{name}] shape={df.shape}, mean={df.iloc[-1].mean():.4f}")
    else:
        print(f"  [{name}] FAILED")

# ===========================================================================
# 5. Evaluate factors
# ===========================================================================
print("\n--- Factor evaluation: momentum_20d ---")
returns = ctx["returns"]
factor_df = results["momentum_20d"]

evaluator = FactorEvaluator(
    factor=factor_df,
    returns=returns,
    n_groups=5,
    holding_period=1,
)

report = evaluator.full_report()
print(report)

# ===========================================================================
# 6. Demonstrate custom operator registration
# ===========================================================================
print("\n--- Custom operator ---")
from mini_bloomberg.factors.utils import register_operator

@register_operator("ts_momentum")
def ts_momentum(df: pd.DataFrame, fast: int = 5, slow: int = 20) -> pd.DataFrame:
    "Momentum ratio: short moving average / long moving average - 1."
    return df.rolling(fast).mean() / df.rolling(slow).mean() - 1

# The operator is immediately available in expressions
custom_factor = engine.evaluate("rank(ts_momentum(close, 5, 20))")
print(f"  Custom factor shape: {custom_factor.shape}")

print("\nDemo complete!")
