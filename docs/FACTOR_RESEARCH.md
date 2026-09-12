# Factor Research: Usage and Recovery Notes

Recovered from Claude exports downloaded on 2026-09-11 and integrated with the MINIBB CLI, web interface and AI tools.

## Usage

Restart the MINIBB backend after Python changes, then refresh the web page. Select ALPHA in the sidebar or enter a command in the web terminal or interactive CLI.

Operator List opens a searchable reference of registered operators, signatures, categories, implementation notes and connected data fields. Opening the manual does not fetch market prices. Data Coverage in each ALPHA result shows the actual non-missing percentage for every loaded field.

```text
ALPHA <GO>
ALPHA --days 365 <GO>
ALPHA --symbols AAPL,MSFT,NVDA,AMZN,GOOGL,META,JPM,V,XOM,JNJ,PG,UNH --days 180 <GO>
ALPHA --start 2025-01-01 --end 2025-12-31 --expression rank(ts_delta(close, 5)) <GO>
ALPHA --expression rank(ts_delta(close, 5)) <GO>
ALPHA --expression trade_when(volume > ts_mean(volume, 20), rank(-ts_delta(close, 5)), -1) <GO>
ALPHA --operators <GO>
ALPHA --dataset demo <GO>
ALPHA --dataset prices.csv --expression rank(ts_mean(close, 20)) <GO>
```

### Online market data

The default dataset is `market`. US equities use the existing FMP history route with OpenBB/yfinance fallback; other supported markets use OpenBB. Existing configuration and the one-hour provider cache are reused. No additional SDK is required. The default universe is the 12 US securities shown above, an example research universe rather than an investment recommendation. It does not follow the currently loaded single security.

`--symbols` accepts 10-50 unique, comma-separated securities. Bare symbols such as `AAPL` mean US equities; use Bloomberg-style identifiers such as `0700 HK Equity` for other markets. `--days` accepts 7-1825 calendar days. Alternatively, use inclusive `--start` and `--end` dates in YYYY-MM-DD format within the last five years; start overrides days.

Results include each security's provider, actual first and last dates, record count and fetch timestamp. Old cache entries may have an unknown fetch timestamp. Missing history is not fabricated. A failed security causes an explicit error rather than synthetic substitution or silent removal.

These are daily historical bars, not a streaming tick feed. Caching, vendor delays and an unfinished trading session affect freshness. Dates are aligned by union; missing prices are not forward-filled. Mixed trading calendars can reduce valid cross-sectional sample sizes. Prices retain provider adjustment conventions and native currencies; consistent adjustment across providers is not guaranteed.

### Synthetic and local data

Select `--dataset demo` explicitly for a deterministic synthetic dataset with 252 business days and 20 fictional securities. It requires no API credentials.

Place local data in `MINIBB/data/factors/prices.csv`. Required long-format columns are `trade_date,ts_code,close`; optional numeric fields include `open,high,low,volume,amount`. Dates use YYYY-MM-DD or YYYYMMDD. At least 10 securities and 3 dates are required. Each date/security pair must be unique. Security codes retain leading zeros and missing prices are not forward-filled. Limits: 20 MB, 500 securities and 5000 dates.

Accessible data is not automatically connected to ALPHA. Financial statements, valuations, news and estimates require numeric date-by-security matrices, consistent frequencies and units, and actual publication dates to prevent look-ahead bias. Text must be converted into numeric signals. CSV files can supply additional aligned numeric fields, including industry codes for group operators.

### Expressions and results

Expressions support numbers, string parameters, arithmetic, powers, comparisons, logical operations, keyword arguments, registered function calls and intermediate assignments such as `x = ...; rank(x)`. Arbitrary Python execution, attribute access and imports are not supported. The complete BRAIN syntax is not implemented, including `?:`. Keyword-named calls `and(...)`, `or(...)` and `not(...)` are supported.

Results include coverage, IC, Rank IC, information ratios, latest factor rankings and cumulative quintile and long-short values. The web interface charts the long-short curve; the complete quintile series is returned in `data.curve`.

## Recovery provenance

- The factor engine was recovered from a May 2026 project conversation: 19 source files and 4 recorded edits. Personal conversation exports and account metadata are not distributed with this repository.
- The original 102-entry operator CSV was recovered from tool output as `operators_wq_brain_102.csv`.
- The local, untracked `factor_restore_manifest.json` records original source hashes and applied edits. `factor_operator_inventory.json` lists registered and missing names.

No shell commands from the exports were executed. The recovery did not modify `.env`. The Python namespace is `mini_bloomberg.factors`, integrated through the existing function and rendering layers.

## Changes from the recovered implementation

- Replaced the parser that skipped invalid characters with a restricted AST interpreter supporting comparisons, keyword arguments and logical operator names.
- Fixed initial holdings, exit priority and scalar conditions in `trade_when`.
- Preserved CSV security identifiers, rejected duplicate observations and disabled implicit price filling when calculating returns.
- Evaluation accepts unshifted daily returns and aligns forward returns internally. Multi-day returns compound over the holding period; overlapping multi-day returns cannot be compounded directly into a portfolio curve.
- Quantile transforms use the Python standard library rather than adding scipy.
- Online data integration adds provider/date metadata, nonmutating history ordering, empty-FMP fallback and an explicit OpenBB calendar range.

## Limitations

This is a working local research prototype, not a complete BRAIN platform. There are 118 registered names including aliases, covering 94 of the 102 names in the original CSV. Eight remain unimplemented: `ts_target_tvr_decay`, `ts_target_tvr_hump`, `generate_stats`, `group_backfill`, `combo_a`, `self_corr`, `in`, `universe_size`.

Name coverage does not establish numerical equivalence with BRAIN. Rolling minimum samples, rank normalization, some arguments, matrix semantics of vector/reduction operators and simplified implementations such as `pasteurize` still require compatibility validation. Unsupported names and arguments return errors.

Return curves are gross research diagnostics. A signal at close T is paired with the close-T-to-close-T+1 return, without execution constraints, fees, slippage, delisting returns or financing costs. Provide consistently adjusted prices and a point-in-time universe. No trading account is accessed or traded by default.

Tushare and JoinQuant loaders remain in the recovered package; their optional SDKs are not installed or network-validated. ALPHA uses existing FMP/OpenBB histories, explicit synthetic data or local CSV files. This guide supersedes historical instructions in the recovered README.

## English source migration

Exact pre-translation copies are stored outside MINIBB in `../MINIBB_originals_zh_20260912/`, preserving their relative paths. The archive includes an SHA-256 manifest and is not imported by the application. Active comments, docstrings, messages and documentation are English, including operator descriptions shown on the web.

Third-party spreadsheet locale constants and financial-name matching aliases retain their original values through Unicode escapes. They are compatibility data, not interface copy; changing their meanings would break parsing or matching. Dependencies, Git history, caches and private environment settings are not translation targets.

## Validation

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python -m unittest discover -s tests -p 'test_factor*.py' -v
```

Checks cover expressions, invalid input, future-lag rejection, trading state, forward-return alignment, missing observations, CSV parsing, strict JSON, tool registries and the web API. Web scripts also pass Node syntax validation. Full operator equivalence and strategy effectiveness have not been established.

A live connection and calculation check on 2026-09-12 retrieved 62 daily observations per security for 12 US equities, covering 2026-06-15 through 2026-09-11, all from OpenBB/yfinance. Provider information and metrics are recorded locally in the untracked `factor_market_smoke.json`. This verifies connectivity and calculation, not investment performance.
