Put long-format UTF-8 CSV datasets here, then run:

`ALPHA --dataset prices.csv --expression rank(ts_delta(close, 5))`

Required columns: `trade_date,ts_code,close`. Optional numeric fields: `open,high,low,volume,amount`.
Dates use `YYYY-MM-DD` or `YYYYMMDD`; security codes are preserved as strings.
One row per date/security, at least 10 securities and 3 dates. No duplicate rows.
Use consistently adjusted prices and a point-in-time universe. Missing observations are not forward-filled.
ALPHA defaults to online market histories through existing FMP/OpenBB sources. The explicit `--dataset demo` option uses deterministic synthetic data and requires no account or API key.
