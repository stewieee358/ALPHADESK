# ALPHADESK

A Bloomberg-style CLI and web terminal for equity, FX, and quantitative factor research, powered by **OpenBB + FMP + yfinance + Tushare Pro** for data and **Claude** as a natural-language orchestrator.

```
╭─────────────────────────────────────────────────────────────────────────────╮
│  ALPHADESK  Equity & FX Analysis Terminal                              │
│                                                                             │
│  Equity: DES / FA / GP / ANR / COMP / RV / RPT / NEWS / DCF / QTR          │
│  Factors: ALPHA / Operator List / Data Coverage                            │
│  FX:     FXIP / FXCA / FXHV / FRD / WCR                                   │
│  Prefix with ? to ask the AI analyst. HELP <GO> for all commands.          │
│                                                                             │
│  Run in terminal (CLI) or browser (Web UI at localhost:8000)                │
╰─────────────────────────────────────────────────────────────────────────────╯

ALPHADESK> AAPL US Equity <GO>
Security loaded: AAPL US Equity

ALPHADESK> DES <GO>
╭─────────────────────── DES  Apple Inc.  AAPL ─────────────────────────────╮
│  Name        Apple Inc.    Market Cap    $3.87T                            │
│  Sector      Technology    Beta          1.109                             │
│  Exchange    NMS           Dividend Yld  0.39%                             │
╰────────────────────────────────────────────────────────────────────────────╯

ALPHADESK> ? compare NVDA and AMD profitability <GO>
╭──────────────────────────────── AI Analyst ────────────────────────────────╮
│  NVDA wins on every metric — by a wide margin. Gross margin 71% vs 49%.   │
│  NVDA generated more FCF ($96.7B) than AMD's entire revenue ($34.6B)...   │
╰────────────────────────────────────────────────────────────────────────────╯
```

---

## Features

### What's new in V2

| Feature | What you can do |
|---|---|
| `ALPHA` factor research | Evaluate expressions on daily market data, a local CSV, or deterministic synthetic demo data |
| Operator List | Search registered operators, signatures, categories, implementation notes, and connected fields in the web interface; use `ALPHA --operators` in the terminal |
| Data Coverage and results | Inspect field coverage, provider and date provenance, IC, Rank IC, information ratios, latest rankings, and quintile/long-short curves |
| `NEWS` | Retrieve company headlines with publication dates and summaries |
| `DCF` command | New standalone access to V1's existing valuation model, without generating an RPT or requesting AI insights; the underlying valuation algorithm is unchanged |
| `QTR` | Inspect quarterly income statements, balance sheets, and cash flows |
| Tushare Pro A-share data | Search and analyse Shanghai, Shenzhen, and Beijing listed equities in the CLI and Web UI |
| Configurable AI endpoint | Configure the API endpoint and model through `ANTHROPIC_BASE_URL` and `CLAUDE_MODEL`; see [Setup](#setup) |

The four new commands (`ALPHA`, `NEWS`, `DCF`, and `QTR`) are available in the
interactive CLI, web command bar, and AI tools.

### Try the new commands

Start `uv run mini-bb`, then enter these commands in its interactive prompt,
or enter them in the web command bar:

```text
AAPL US Equity <GO>
NEWS --limit 10 <GO>
DCF --years 4 <GO>
QTR --quarters 8 --statement IS <GO>
QTR --quarters 4 --statement CF <GO>
ALPHA --dataset demo <GO>
ALPHA --operators <GO>
ALPHA --days 180 --expression rank(ts_delta(close, 5)) <GO>
```

`NEWS --limit` accepts 1–50 headlines (default 10). `QTR --quarters` accepts
1–40 quarters (default 8), subject to provider availability; omit `--statement`
for all statements, or select `IS`, `BS`, or `CF`.

### Factor research

`ALPHA` defaults to a 12-stock example universe using FMP/OpenBB market histories;
it does not use the currently loaded single security. Select 10–50 securities
and a lookback of 7–1825 calendar days, or provide `--start` and `--end` dates:

```text
ALPHA --symbols AAPL,MSFT,NVDA,AMZN,GOOGL,META,JPM,V,XOM,JNJ,PG,UNH --days 180 <GO>
ALPHA --start 2025-01-01 --end 2025-12-31 --expression rank(ts_delta(close, 5)) <GO>
ALPHA --dataset prices.csv --expression rank(ts_mean(close, 20)) <GO>
```

Place `prices.csv` in `data/factors/` with `trade_date,ts_code,close` columns
and at least 10 securities and 3 dates. Optional fields include
`open,high,low,volume,amount`. Use `ALPHA --dataset demo` for a credentials-free
synthetic example; market-data failures do not silently switch to demo data.

The web results include a long-short chart, field coverage, and data provenance.
Expressions support registered operators, comparisons, and assignments such as
`x = ts_delta(close, 5); rank(x)`. Only a subset of BRAIN expression syntax is
implemented. Market histories can differ in calendars, currency, and adjustment
conventions; see [factor research setup, data sources and limitations](docs/FACTOR_RESEARCH.md)
for evaluation assumptions and supported data.

**Equity**

| Function | Bloomberg equivalent | What it does |
|---|---|---|
| `DES` | Description | Company profile: name, sector, market cap, identifiers |
| `FA` | Financial Analysis | 4-year income statement, balance sheet, cash flow |
| `GP` | Graph Price | ASCII price chart via plotext |
| `ANR` | Analyst Recommendations | Consensus target price + buy/hold/sell breakdown |
| `COMP` | Comparables | Peer table: margins, EBITDA, debt, beta |
| `RV` | Relative Value | Valuation multiples + margin comparison vs. peer group |
| `RPT` | (custom) | Full investment-bank-style HTML equity report with DCF valuation model (opens in browser) |
| `NEWS` | Company News | Recent headlines, publication dates, and summaries; `--limit N` |
| `DCF` | DCF Valuation | Standalone WACC, FCFF projections, fair value, and sensitivity grid; `--years N` |
| `QTR` | Quarterly Financials | Quarterly IS/BS/CF; `--quarters N`, optional `--statement IS\|BS\|CF` |

**FX**

| Function | Bloomberg equivalent | What it does |
|---|---|---|
| `FXIP` | FX Rates Monitor | G10 or EM spot rates vs USD — price, 1d change, 52W range |
| `FXCA` | FX Calculator | Convert an amount between any two currencies |
| `FXHV` | FX Historical Vol | Annualised historical volatility across 7 windows (10d – 1y) |
| `FRD` | FX Forward Rates | CIP-implied forward curve across 9 tenors (O/N → 1Y) |
| `WCR` | World Currency Ranker | G10/EM currencies ranked by performance |

**AI**

| Command | What it does |
|---|---|
| `? <query>` | Claude agent with tool-use — runs any function and synthesises an answer |
| `CLEAR HISTORY <GO>` | Wipe the agent's in-session conversation memory |

**Interfaces**: CLI terminal (Rich tables, streaming agent) and Web UI (Bloomberg-style browser terminal at `localhost:8000`).

**Global equity coverage**: US, HK, JP, FR, DE, UK and more via `SYMBOL EXCHANGE Equity` format.

---

## Architecture

```
                      ┌─────────────────────────────────┐
                      │         Entry Points             │
                      │                                  │
                      │  CLI: uv run mini-bb             │
                      │  Web: uvicorn …web.server:app    │
                      └──────────────┬──────────────────┘
                                     │
               ┌─────────────────────┴──────────────────────┐
               │                                            │
               ▼                                            ▼
    cli/repl.py                               web/server.py (FastAPI)
    └─ cli/dispatcher.py                      ├── GET  /
       routes: TICKER | FUNCTION | ? query    ├── POST /api/command
                                              ├── POST /api/agent
                                              └── GET  /api/status
               │                                            │
               └─────────────────────┬──────────────────────┘
                                     │  (same function layer)
                                     ▼
                             functions/
                       DES / FA / GP / ANR / COMP / RV / RPT   (equity)
                       FXIP / FXCA / FXHV / FRD / WCR          (FX)
                       BloombergFunction ABC — .run() + .tool_schema()
                                     │
                                     ▼
                               data/
                       provider routers → FMP (US) or OpenBB/yfinance (non-US)
                       Pydantic models, cached via diskcache
                                     │
                          ┌──────────┴──────────┐
                          ▼                     ▼
                    render/                 agents/
                    cli_renderer.py         orchestrator.py  ← streaming tool-use loop
                    html_renderer.py        prompts.py       ← system prompt (editable)
                    (Rich + plotext)        tools.py         ← auto tool specs from functions
```

**Key design**: CLI commands, the web API, and the LLM agent all call the **same** `fn.run()` — zero code duplication. The Anthropic client is a singleton in `core/llm.py` shared across the process.

---

## Setup

### Repository contents

- `src/mini_bloomberg/`: application, web assets, and factor research engine.
- `tests/`: unit tests using fixture market data.
- `docs/`, `Bloomberg Functions/`, `Schema for stocks analysis/`: reference documentation.
- `pyproject.toml` and `uv.lock`: package configuration and locked dependencies.
- `.env.example`: configuration template without credentials.

Generated HTML reports, local factor datasets, caches, logs, and `.env` stay on
your machine. Existing reports are preserved when removed from Git tracking.

Run checks after installing dependencies:

```bash
uv lock --check
uv run python -m unittest discover -s tests -v
```

GitHub Actions runs the same unit test suite on pushes and pull requests.

### 1. Prerequisites

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) — `pip install uv`

### 2. Install

```bash
git clone https://github.com/stewieee358/ALPHADESK.git ALPHADESK
cd ALPHADESK
uv sync --locked --extra dev
```

### 3. API Keys

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env`. Keep credentials in
your local `.env`; only the placeholder `.env.example` belongs in Git.

| Key | Where to get it | Required for |
|---|---|---|
| `FMP_API_KEY` | [financialmodelingprep.com](https://financialmodelingprep.com/developer/docs) (free) | FA, GP, ANR, COMP, RV, RPT |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | `? <query>` AI agent |
| `OPENBB_PAT` | [my.openbb.co](https://my.openbb.co/app/platform/pat) (optional) | Enhanced non-US equity data |
| `TUSHARE_TOKEN` | [Tushare Pro](https://tushare.pro/) | A-share DES, GP, FA, QTR, ANR, COMP, RV, DCF, and RPT |
| `TUSHARE_API_URL` | Official endpoint when blank, or a Tushare-compatible gateway URL | Optional endpoint override for the same A-share functions |

> **FMP free tier**: 250 calls/day. Equity data is cached 24h so normal use stays well within limits.
> **FX functions** (FXIP/FXCA/FXHV/FRD/WCR) use **yfinance only** — no API key required.

#### Tushare Pro setup for A-shares

ALPHADESK reads the Tushare credentials from the project-root `.env` file.
The same configuration is used by the CLI, Web UI, and Python/Jupyter code.
Create `.env` from the template, then set:

```dotenv
TUSHARE_TOKEN=your_tushare_pro_token
TUSHARE_API_URL=https://t.xiaodefa.top/
```

`TUSHARE_TOKEN` is the API token issued for your Tushare Pro account. Set
`TUSHARE_API_URL` when that token is accessed through a compatible gateway;
leave it blank to use the Tushare SDK's official endpoint. Do not commit the
real token to Git. Available records still depend on the points, API permissions,
and entitlements attached to the account. See the
[Tushare API documentation](https://tushare.pro/document/2?doc_id=14) for the
provider's endpoint and permission details.

For mainland-China equities, the following commands use Tushare Pro:

| Command | A-share data used |
|---|---|
| `DES` | Company name, exchange, region, industry, description, market cap, shares, P/E, P/B, P/S, and dividend yield |
| `GP` | Forward-adjusted (`qfq`) daily OHLCV price history |
| `FA` | Annual income statements, balance sheets, and cash-flow statements |
| `QTR` | Quarterly income statements, balance sheets, and cash-flow statements |
| `ANR` | Research-report ratings, broker coverage, and available target-price ranges |
| `COMP` | Same-industry A-share peers selected using market cap, with valuation and profitability metrics |
| `RV` | Relative valuation and margin comparison using the Tushare peer set |
| `DCF` | FCFF valuation using Tushare financial statements, market cap, debt, cash, and share data |
| `RPT` | Full equity report combining the available Tushare profile, price, financial, analyst, peer, and DCF data |

The factor-research loader can use the same `.env` settings from a notebook or
Python script. Its stock list uses native Tushare codes:

```python
from mini_bloomberg.factors import DataLoader

loader = DataLoader(source="tushare")
ctx = loader.load(
    stock_list=["000001.SZ", "600519.SH"],
    start_date="20240101",
    end_date="20241231",
)
```

Passing `token=` or `api_url=` to `DataLoader` overrides the corresponding
`.env` value for that loader instance.

### 4. Run

The CLI and Web UI share the settings in `.env`. The default API endpoint is
`https://api.anthropic.com`. To use an Anthropic-compatible service, set
`ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, and `CLAUDE_MODEL` to the endpoint,
credentials, and model supported by that service.

Restart the existing server after changing `.env`; running the launcher again
while the server is active only opens the browser.

**CLI (terminal)**
```bash
uv run mini-bb                        # launch interactive REPL
uv run mini-bb des "AAPL US Equity"   # one-shot command
```

**Web UI — one-click (Windows)**
```
Double-click  mini-bb.bat
```
The server starts in the background and your browser opens at `http://localhost:8000` automatically. If the server is already running, it just opens the browser.

To pin a Desktop shortcut (run once in PowerShell):
```powershell
powershell -ExecutionPolicy Bypass -File create_shortcut.ps1
```

**Web UI — manual start**
```bash
# Install web server deps (one-time)
uv add fastapi uvicorn

# Start the server
uvicorn mini_bloomberg.web.server:app --reload --port 8000
```
Then open **http://localhost:8000** in your browser.

The web UI reads the same `.env` file as the CLI — no extra config needed.

---

## Usage

### REPL commands

```
── Equity ──────────────────────────────────────────────────────────────────
AAPL US Equity <GO>              Load a security
DES <GO>                         Company description
FA <GO>                          Financial analysis (4 years)
GP <GO>                          Price chart (default 1 year)
GP --days 90 <GO>                Price chart (custom period)
ANR <GO>                         Analyst ratings
COMP <GO>                        Peer comparison table
RV <GO>                          Relative value — valuation vs. peers
RPT <GO>                         Full HTML equity report → reports/<TICKER>_<DATE>.html
NEWS --limit 10 <GO>             Recent company headlines and summaries
DCF --years 4 <GO>               Existing DCF model, called independently of RPT
QTR --quarters 8 <GO>            Available quarterly financial statements
QTR --quarters 4 --statement BS <GO>   Quarterly balance sheets only

── Factor research ─────────────────────────────────────────────────────────
ALPHA <GO>                       Evaluate the default expression on market data
ALPHA --dataset demo <GO>        Evaluate synthetic data without credentials
ALPHA --operators <GO>           Show the operator and field reference
ALPHA --dataset prices.csv --expression rank(ts_delta(close, 5)) <GO>

── FX ──────────────────────────────────────────────────────────────────────
FXIP <GO>                        G10 spot rates vs USD
FXIP --group em <GO>             EM spot rates vs USD
FXCA --from USD --to JPY --amount 1000 <GO>   Convert 1000 USD → JPY
FXHV --base EUR --quote USD <GO> EUR/USD historical volatility
FRD --base EUR --quote USD <GO>  EUR/USD forward rate curve
WCR <GO>                         G10 currencies ranked by performance
WCR --group em --sort-by 1m <GO> EM currencies ranked by 1-month return

── General ─────────────────────────────────────────────────────────────────
? <your question> <GO>           Ask the AI analyst (remembers this session's context)
CLEAR HISTORY <GO>               Wipe the AI analyst's conversation memory
HELP <GO>                        List all commands
QUIT <GO>                        Exit
```

### Supported ticker formats

```
AAPL US Equity      Apple Inc (NYSE/NASDAQ)
0700 HK Equity      Tencent Holdings (HKEX)
7203 JP Equity      Toyota Motor (Tokyo)
MC FP Equity        LVMH (Euronext Paris)
SAP GR Equity       SAP SE (XETRA)
HSBA LN Equity      HSBC Holdings (London)
600519 CH Equity    Kweichow Moutai (Shanghai, via Tushare Pro)
000001 CH Equity    Ping An Bank (Shenzhen, via Tushare Pro)
```

For mainland-China equities, `CH` automatically infers `.SH`, `.SZ`, or `.BJ`
from the numeric code. When `TUSHARE_TOKEN` is configured, DES, GP, FA, QTR,
ANR, COMP, RV, DCF, and RPT use Tushare Pro data. Tushare NEWS requires a
separate news/announcement entitlement and therefore is not enabled by default.

In the Web UI command bar, A-shares can be found by six-digit code, full or
partial Chinese company name, Tushare code, or pinyin abbreviation. For example,
all of the following searches can return the standard Bloomberg-style choice
`600519 CH Equity`:

```text
600519
600519.SH
贵州茅台
茅台
GZMT
```

The dropdown shows the standard ticker together with company name, exchange,
and industry. Select the result first, then run `DES`, `GP`, `FA`, `COMP`,
`DCF`, or another supported equity command. In the CLI, enter the standard
ticker directly, for example `600519 CH Equity <GO>`.

### Direct subcommands (no REPL)

```bash
uv run mini-bb des  "AAPL US Equity"
uv run mini-bb fa   "AAPL US Equity" --years 4
uv run mini-bb gp   "AAPL US Equity" --days 180
uv run mini-bb anr  "AAPL US Equity"
uv run mini-bb comp "AAPL US Equity"
```

Only `des`, `fa`, `gp`, `anr`, and `comp` are registered as direct shell
subcommands. For `RV`, `RPT`, `NEWS`, `DCF`, `QTR`, `ALPHA`, and FX commands,
start `uv run mini-bb` and use the interactive prompt, or use the web command bar.

---

## Web UI

Start the FastAPI server (`uv run uvicorn mini_bloomberg.web.server:app --reload --port 8000`) and open `http://localhost:8000`.

```
┌──────────────────────────────────────────────────────────────────┐
│  ◼ ALPHADESK                              [status bar]      │
├──────────────────────────────────────────────────────────────────┤
│  Command bar:  AAPL US Equity <GO>    [Enter to execute]         │
├────────────┬────────────────────────────────┬────────────────────┤
│  Sidebar   │  OUTPUT  │  RAW DATA           │  AI Analyst        │
│  ─────     │  ─────── │                     │  ─────────────     │
│  Equities  │  Result  │  Full JSON for      │  Type a question   │
│  DES FA GP │  tables, │  debugging          │  or prefix cmd     │
│  ANR COMP  │  charts, │                     │  with ?            │
│  RV RPT    │  RPT HTML│                     │                    │
│  NEWS DCF  │          │                     │                    │
│  QTR ALPHA │          │                     │                    │
│  ─────     │          │                     │  Tool call log     │
│  FX        │          │                     │  shown here        │
│  FXIP FXCA │          │                     │                    │
│  FXHV FRD  │          │                     │                    │
│  WCR       │          │                     │                    │
└────────────┴──────────┴─────────────────────┴────────────────────┘
```

### API routes

| Method | Route | What it does |
|---|---|---|
| `GET` | `/` | Serves the Bloomberg-style terminal UI (`index.html`) |
| `POST` | `/api/command` | Execute any Bloomberg command; returns structured JSON |
| `POST` | `/api/agent` | Run a Claude AI agent query with tool-use |
| `GET` | `/api/status` | Health check + currently loaded ticker |

### Web UI features

- **Command bar**: same Bloomberg-style syntax as the interactive CLI — `AAPL US Equity`, `NEWS --limit 10`, `DCF`, `QTR --statement IS`, `ALPHA --dataset demo`, `? compare AAPL and MSFT`
- **Tab autocomplete**: suggests commands and tickers as you type
- **OUTPUT tab**: formatted tables, key-value grids, rating badges, inline RPT HTML
- **RAW DATA tab**: full JSON response for debugging
- **AI Agent panel**: natural language questions with tool call log; maintains conversation history within the browser session
- **Sidebar shortcuts**: click DES, FA, GP, etc. to fill the command bar; command history
- **Factor research**: ALPHA results show coverage, data sources, rankings, evaluation metrics, and a long-short chart; Operator List provides a searchable operator and field reference

### RPT in the web UI

`RPT <GO>` in the web UI renders the full HTML report **inline** in the Output tab — no need to open a separate file.

---

## Data sources

**Equity**

| Data | US equities | Other non-US equities | Mainland-China A-shares (`CH`) |
|---|---|---|---|
| Company profile | OpenBB/yfinance | OpenBB/yfinance | Tushare `stock_basic`, `stock_company`, and `daily_basic` |
| Annual financials (FA/RPT) | FMP `/stable/income-statement` etc. | OpenBB/yfinance | Tushare `income`, `balancesheet`, and `cashflow` |
| Quarterly financials (QTR / RPT XLSX) | OpenBB → SEC XBRL (`obb.equity.compare.company_facts`, provider `"sec"`) — no API key | yfinance quarterly income statement, balance sheet, and cash flow | Tushare `income`, `balancesheet`, and `cashflow`, converted from cumulative disclosures where applicable |
| Price history | FMP `/stable/historical-price-eod/full` | OpenBB/yfinance | Tushare `pro_bar` with forward adjustment (`qfq`) |
| Price targets | FMP `/stable/price-target-consensus` | — | Tushare `report_rc`, subject to permission and available report fields |
| Analyst ratings | OpenBB/yfinance consensus | OpenBB/yfinance | Tushare `report_rc` |
| Peers | FMP `/stable/stock-peers` | — | Same-industry selection from `stock_basic`, `daily_basic`, and `fina_indicator` |
| Company news (NEWS / RPT) | OpenBB tries yfinance, FMP, then Benzinga | Same provider chain; coverage and credentials vary | Not enabled by default; separate Tushare entitlement required |

**DCF Valuation (standalone DCF / RPT §5)**

Both entry points call the same `compute_dcf()` implementation inherited from
V1. The new command changes access to the model, not its assumptions or accuracy.

| Data | Source | Cache TTL |
|---|---|---|
| Risk-free rate (Rf) | US Treasury — 10-year constant-maturity yield | 4h |
| Equity Risk Premium (ERP) | Damodaran `ctryprem.html` — US implied ERP | 24h |
| Country Risk Premium (CRP) | Damodaran `ctryprem.html` — matched to company domicile | 24h |
| Beta, market cap, shares | yfinance `ticker.info` (via OpenBB equity profile) | 24h |
| FCFF inputs (EBIT, D&A, CapEx, NWC, interest) | FMP annual income statement + cash flow + balance sheet | 24h |

**FX** — all functions use **yfinance only** (ticker format: `EURUSD=X`)

| Data | Source | Cache TTL |
|---|---|---|
| Spot rates, 52W range | yfinance 1y history | 5 min |
| Historical OHLCV (FXHV/FRD) | yfinance 1–2y history | 1h |
| Currency performance (WCR) | yfinance 1y history | 10 min |
| Forward rates (FRD) | CIP formula + hardcoded approx. rates | 1h |

**Factor research and optional loaders**

| Input | Integration status |
|---|---|
| FMP / OpenBB daily histories | Connected to `ALPHA --dataset market` (the default); provider/date provenance included |
| Synthetic demo | Connected to `ALPHA --dataset demo`; deterministic generated data |
| Local CSV | Connected to `ALPHA --dataset prices.csv`; files live in `data/factors/` |
| Tushare / JoinQuant factor loaders | Supported through `factors/data/loader.py`; Tushare uses `TUSHARE_TOKEN` and optional `TUSHARE_API_URL`, while JoinQuant requires its own SDK and credentials |

See [factor research documentation](docs/FACTOR_RESEARCH.md) for details.

---

## RPT — HTML Equity Report

`RPT <GO>` generates a self-contained investment-bank-style HTML report and writes it to `reports/<TICKER>_<YYYYMMDD>.html`.

**Report sections:**

| # | Section | Content |
|---|---|---|
| 1 | Company Profile | Key identifiers, description, exchange info |
| 2 | Insights | AI-generated "What happened?" + "Our thoughts"; compact analyst consensus + trading data (52w range, avg vol, beta, P/BV …) |
| 3 | Financial Statements | 4-year income statement, balance sheet, cash flow — side-by-side annual columns; XLSX download |
| 4 | Financial Ratios | Profitability, leverage, efficiency — 4 years |
| 5 | Valuation | DCF fair value, WACC, upside %, terminal growth, risk-free rate — KPI strip + XLSX valuation model download |
| 6 | Valuation Multiples | 8 metric cards (P/E, EV/EBITDA, FCF Yield, …) |
| 7 | Peer Comparison | Subject ticker highlighted in peer table |

The **Insights section** (§2) makes a silent call to `claude-haiku-4-5-20251001` with recent news headlines and financial summary — cached 24h per ticker. Right-hand column shows analyst consensus (rating pill, price target, upside %) and a trading data table derived from 1-year price history.

The **Valuation section** (§5) uses the existing DCF model when sufficient data
is available and exposes a one-click **XLSX download** with four sheets. This
report capability predates V2; the standalone `DCF` command reuses its model.

| Sheet | Content |
|---|---|
| DCF Projections | Historical FCFF (3–4 years) + 5-year projection; discount factors and PV of each FCFF |
| WACC Derivation | Full CAPM build — Rf, β, ERP, CRP, Ke, Kd, capital structure weights, WACC |
| Valuation Summary | Enterprise value bridge (PV FCFFs + terminal value → equity value → price per share); 5×5 sensitivity table (WACC × terminal growth) |
| Limitations & Assumptions | All model assumptions, data sources, known limitations, and disclaimer |

**DCF methodology** (follows [Damodaran](https://pages.stern.nyu.edu/~adamodar/) framework):
- **FCFF** = EBIT × (1 − T) + D&A − ΔNWC − CapEx, from FMP annual statements
- **Revenue projection**: 3–4 year historical CAGR, decayed 10% per year toward long-run growth
- **WACC** via CAPM: Ke = Rf + β × (ERP + CRP); Kd = interest expense / total debt
- **Risk-free rate**: live 10-year US Treasury yield (cached 4h)
- **ERP & CRP**: live from Damodaran `ctryprem.html` (cached 24h); CRP is non-zero for non-US companies
- **Terminal value**: Gordon Growth Model with 2.5% perpetuity growth rate
- Sensitivity grid spans WACC ± 2% and terminal growth 1.5%–3.5%

P/E ratios show **N/M** (not meaningful) when the absolute value exceeds 999× — e.g. near-zero EPS years.

Open the `.html` file in any browser. Use browser **Print → Save as PDF** for a hard copy. No extra dependencies — the report is pure HTML/CSS/JS with Google Fonts loaded via CDN.

---

## AI Agent

The `?` prefix routes to the model selected by `CLAUDE_MODEL` in `.env`
(`claude-sonnet-4-6` by default). The configured endpoint must support that model.
Registered AI tools are `ALPHA`, `DES`, `FA`, `GP`, `ANR`, `COMP`, `RPT`, `RV`,
`NEWS`, `DCF`, and `QTR`. FX commands currently have no registered AI tools.

The agent uses **prompt caching** on the system prompt and **streaming output** so you see the answer token-by-token. It runs tool calls in **parallel** (e.g. `FA` for two tickers simultaneously).

**Session memory**: the agent maintains a sliding-window conversation history
within each session. This is not durable storage across process restarts.

```
ALPHADESK> ? what is AAPL's revenue trend? <GO>
ALPHADESK> ? how does that compare to MSFT? <GO>    ← agent references AAPL context
ALPHADESK> CLEAR HISTORY <GO>                        ← wipe memory for a fresh start
```

| `.env` variable | Default | Effect |
|---|---|---|
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Model used by the `?` agent |
| `AGENT_MEMORY_TURNS` | `20` | Number of past messages kept in the sliding window |

---

## Tech stack

```
Data        openbb, httpx, pydantic, diskcache
Factors     pandas, numpy, restricted expression interpreter
CLI         typer, rich, plotext, prompt-toolkit
Web         fastapi, uvicorn
LLM         anthropic (claude-sonnet-4-6 / claude-haiku-4-5 for RPT insights)
Infra       uv, python-dotenv, pytest
```

---

## Known limitations

**Equity**
- **India BSE**: ticker mapping unreliable via yfinance
- **COMP for non-US**: FMP peer list is US-centric; non-US peers may be incomplete
- **ANR for non-US**: price targets only available for US tickers via FMP
- **Native currency in COMP**: non-US revenue displays in native currency, not USD-converted
- **Bank / financial sector IS**: banks (e.g. HK-listed Chinese banks) use a different income statement structure — no Cost of Revenue, Gross Profit, Operating Income, or EBITDA. These fields show N/A. Net Interest Income and other bank-specific line items are not currently mapped.
- **Semi-annual reporters**: companies that publish only H1 and annual results (e.g. Lenovo 00992 HK) will show data only for Q2 and the annual column in the XLSX download. Q1, Q3, Q4 cells are blank — this reflects the company's actual reporting cadence, not a data gap.

**Tushare Pro / A-shares**
- **Account permissions**: endpoint access and field coverage depend on the configured Tushare account's points and entitlements; an unavailable endpoint may return no data even when the token itself is valid.
- **NEWS entitlement**: A-share news and announcements are not enabled by default because the corresponding Tushare interface requires separate permission.
- **DCF beta**: the current Tushare company profile does not provide beta. A-share DCF therefore uses the valuation model's fallback beta of `1.0`; treat the result as a scenario estimate rather than an investment recommendation.
- **Price convention**: A-share `GP` history uses Tushare forward-adjusted (`qfq`) prices, so historical values may differ from unadjusted exchange closes.

**DCF Valuation**
- **V2 scope**: standalone access was added; the underlying V1 model and its limitations remain unchanged.
- **Beta relevering**: uses raw yfinance beta (already levered); Damodaran unlevered/relevered beta is not applied
- **Non-US tickers**: CRP is added to ERP, but the risk-free rate stays US 10Y Treasury — a local sovereign yield would be more appropriate
- **Cyclical / loss-making companies**: negative historical FCFF (e.g. companies with large restructuring charges) propagates into projections; treat the output as directional only
- **GAAP only**: no non-GAAP adjustments — stock-based compensation, restructuring costs, and acquired-intangible amortisation are not stripped out
- **Data source fallback**: if the US Treasury or Damodaran fetch fails, hardcoded constants are used (Rf = 4.3%, ERP = 4.46%); a footnote appears in the KPI strip

**FX**
- **FRD forward rates**: computed from hardcoded approximate benchmark rates, not live OIS/SOFR swap points — directionally correct but not trading-grade
- **FXCA cross rates**: routes through USD when a direct yfinance pair is unavailable; minor rounding on exotic crosses

**Factor research**
- **Operator compatibility**: registered names do not guarantee numerical equivalence with BRAIN. Some operators and arguments are unsupported, and several implementations are simplified; see the [operator coverage notes](docs/FACTOR_RESEARCH.md#limitations).
- **Research curves, not execution simulation**: close-T signals are paired with subsequent close-to-close returns. Fees, slippage, order execution, financing costs, and delisting returns are not modeled.
- **Connected fields**: ALPHA currently consumes daily price/volume data. Financial statements, news, and estimates are not automatically available as factor matrices; historical publication-time alignment would be needed.
- **Input and scale limits**: market mode accepts 10–50 securities and up to 1825 calendar days. CSV input is limited to 20 MB, 500 securities, and 5000 dates.
