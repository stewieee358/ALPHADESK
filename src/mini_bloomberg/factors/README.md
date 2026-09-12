# Quant Factor Mining Engine

A local factor research framework inspired by WorldQuant BRAIN, integrated with the MINIBB terminal.

## Structure

- `core/context.py`: aligned data matrices and metadata.
- `core/expression.py`: restricted factor expression interpreter.
- `operators/base.py`: base operator interface.
- `operators/cross_section.py`: cross-sectional ranking, scaling and normalization.
- `operators/time_series.py`: rolling statistics, ranks, correlations and decay weights.
- `operators/math_ops.py`: elementwise mathematics and conditional selection.
- `operators/group.py`: group statistics and neutralization.
- `operators/wq_brain_ops.py`: additional local BRAIN-style operators.
- `data/loader.py`: Tushare, JoinQuant, CSV and DataFrame inputs.
- `backtest/evaluator.py`: IC, quantile returns, turnover and decay analysis.
- `utils/registry.py`: decorator-based operator registration.
- `catalog.py`: operator signatures and data reference for the web manual.
- `main.py`: synthetic-data example.

## Design

All standard inputs are pandas DataFrames with dates as rows and security codes as columns. Operators compose into expressions such as `rank(ts_mean(close, 20))`. Register custom functions with `@register_operator("name")`.

Run the example from the project root with `python -m mini_bloomberg.factors.main` in the installed environment. For the integrated interface use `ALPHA`; use `ALPHA --dataset demo` explicitly for synthetic inputs.

See [the current research guide](../../../docs/FACTOR_RESEARCH.md) for market data, CSV formats, supported syntax and limitations.
