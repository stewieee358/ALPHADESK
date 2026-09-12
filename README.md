# MINIBB-V2 — Mini-Bloomberg

A CLI terminal that mimics Bloomberg for equity and FX analysis, powered by **OpenBB + FMP + yfinance** for data and **Claude** as a natural-language orchestrator.

```
╭─────────────────────────────────────────────────────────────────────────────╮
│  MINI-BLOOMBERG  Equity & FX Analysis Terminal                              │
│                                                                             │
│  Equity: DES / FA / GP / ANR / COMP / RV / RPT                             │
│  FX:     FXIP / FXCA / FXHV / FRD / WCR                                   │
│  Prefix with ? to ask the AI analyst. HELP <GO> for all commands.          │
│                                                                             │
│  Run in terminal (CLI) or browser (Web UI at localhost:8000)                │
╰─────────────────────────────────────────────────────────────────────────────╯

MINI-BB> AAPL US Equity <GO>
Security loaded: AAPL US Equity

MINI-BB> DES <GO>
╭─────────────────────── DES  Apple Inc.  AAPL ─────────────────────────────╮
│  Name        Apple Inc.    Market Cap    $3.87T                            │
│  Sector      Technology    Beta          1.109                             │
│  Exchange    NMS           Dividend Yld  0.39%                             │
╰────────────────────────────────────────────────────────────────────────────╯

MINI-BB> ? compare NVDA and AMD profitability <GO>
╭──────────────────────────────── AI Analyst ────────────────────────────────╮
│  NVDA wins on every metric — by a wide margin. Gross margin 71% vs 49%.   │
│  NVDA generated more FCF ($96.7B) than AMD's entire revenue ($34.6B)...   │
╰────────────────────────────────────────────────────────────────────────────╯
```

---

## Features

**Factor research (restored Claude project)**: `ALPHA <GO>` evaluates a 12-stock example universe using existing FMP/OpenBB daily market histories.
Use `ALPHA --symbols AAPL,MSFT,NVDA,AMZN,GOOGL,META,JPM,V,XOM,JNJ,PG,UNH --days 180` to select a universe and period;
`ALPHA --dataset demo` explicitly selects synthetic data, and
`ALPHA --dataset prices.csv --expression rank(ts_delta(close, 5))` evaluates your own CSV.
Available in the CLI, web sidebar and AI tools. See [factor research setup, provenance and limitations](docs/FACTOR_RESEARCH.md).

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
git clone https://github.com/stewieee358/MINIBB-V2.git MINIBB
cd MINIBB
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

> **FMP free tier**: 250 calls/day. Equity data is cached 24h so normal use stays well within limits.
> **FX functions** (FXIP/FXCA/FXHV/FRD/WCR) use **yfinance only** — no API key required.

### 4. Run

For Qiniu AI, set the following in `.env` (use your Qiniu AI key):

```dotenv
ANTHROPIC_API_KEY=your_qiniu_ai_key
ANTHROPIC_BASE_URL=https://api.qnaigc.com
CLAUDE_MODEL=claude-4.5-sonnet
```

Both the CLI and Web UI use this endpoint. Model access depends on your Qiniu
account. See the [Qiniu Anthropic API documentation](https://apidocs.qnaigc.com/413432574e0).
Restart the existing server after changing `.env`; running the launcher again
while the server is active only opens the browser. For direct Anthropic access,
set `ANTHROPIC_BASE_URL=https://api.anthropic.com` and use an Anthropic key and model ID.

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
```

### Direct subcommands (no REPL)

```bash
uv run mini-bb des  "AAPL US Equity"
uv run mini-bb fa   "AAPL US Equity" --years 4
uv run mini-bb gp   "AAPL US Equity" --days 180
uv run mini-bb anr  "AAPL US Equity"
uv run mini-bb comp "AAPL US Equity"
uv run mini-bb rv   "AAPL US Equity"
uv run mini-bb rpt  "AAPL US Equity"
```

---

## Web UI

Start the FastAPI server (`uvicorn mini_bloomberg.web.server:app --reload --port 8000`) and open `http://localhost:8000`.

```
┌──────────────────────────────────────────────────────────────────┐
│  ◼ MINI-BLOOMBERG                              [status bar]      │
├──────────────────────────────────────────────────────────────────┤
│  Command bar:  AAPL US Equity <GO>    [Enter to execute]         │
├────────────┬────────────────────────────────┬────────────────────┤
│  Sidebar   │  OUTPUT  │  RAW DATA           │  AI Analyst        │
│  ─────     │  ─────── │                     │  ─────────────     │
│  Equities  │  Result  │  Full JSON for      │  Type a question   │
│  DES FA GP │  tables, │  debugging          │  or prefix cmd     │
│  ANR COMP  │  charts, │                     │  with ?            │
│  RV RPT    │  RPT HTML│                     │                    │
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

- **Command bar**: same Bloomberg-style syntax as the CLI — `AAPL US Equity`, `DES`, `FA`, `GP --days 90`, `? compare AAPL and MSFT`
- **Tab autocomplete**: suggests commands and tickers as you type
- **OUTPUT tab**: formatted tables, key-value grids, rating badges, inline RPT HTML
- **RAW DATA tab**: full JSON response for debugging
- **AI Agent panel**: natural language questions with tool call log; maintains conversation history within the browser session
- **Sidebar shortcuts**: click DES, FA, GP, etc. to fill the command bar; command history

### RPT in the web UI

`RPT <GO>` in the web UI renders the full HTML report **inline** in the Output tab — no need to open a separate file.

---

## Data sources

**Equity**

| Data | US equities | Non-US equities |
|---|---|---|
| Company profile | OpenBB/yfinance | OpenBB/yfinance |
| Annual financials (FA/RPT) | FMP `/stable/income-statement` etc. | OpenBB/yfinance |
| Quarterly financials (RPT XLSX) | OpenBB → SEC XBRL (`obb.equity.compare.company_facts`, provider `"sec"`) — no API key | yfinance `.quarterly_income_stmt` / `.quarterly_balance_sheet` |
| Price history | FMP `/stable/historical-price-eod/full` | OpenBB/yfinance |
| Price targets | FMP `/stable/price-target-consensus` | — |
| Analyst ratings | OpenBB/yfinance consensus | OpenBB/yfinance |
| Peers | FMP `/stable/stock-peers` | — |

**DCF Valuation (RPT §5)**

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

The **Valuation section** (§5) runs a full DCF model on every `RPT` call and exposes a one-click **XLSX download** with four sheets:

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

The `?` prefix routes to Claude (`claude-sonnet-4-6` by default, switchable to `claude-opus-4-7` via `CLAUDE_MODEL` in `.env`).

The agent uses **prompt caching** on the system prompt and **streaming output** so you see the answer token-by-token. It runs tool calls in **parallel** (e.g. `FA` for two tickers simultaneously).

**Persistent memory**: the agent maintains a sliding-window conversation history within each session — it remembers earlier exchanges and can reference them without re-fetching data.

```
MINI-BB> ? what is AAPL's revenue trend? <GO>
MINI-BB> ? how does that compare to MSFT? <GO>    ← agent references AAPL context
MINI-BB> CLEAR HISTORY <GO>                        ← wipe memory for a fresh start
```

| `.env` variable | Default | Effect |
|---|---|---|
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Model used by the `?` agent |
| `AGENT_MEMORY_TURNS` | `20` | Number of past messages kept in the sliding window |

---

## Tech stack

```
Data        openbb, httpx, pydantic, diskcache
CLI         typer, rich, plotext, prompt-toolkit
Web         fastapi, uvicorn
LLM         anthropic (claude-sonnet-4-6 / claude-haiku-4-5 for RPT insights)
Infra       uv, python-dotenv, pytest
```

---

## Known limitations

**Equity**
- **Chinese A-shares**: requires tushare/akshare — not supported
- **India BSE**: ticker mapping unreliable via yfinance
- **COMP for non-US**: FMP peer list is US-centric; non-US peers may be incomplete
- **ANR for non-US**: price targets only available for US tickers via FMP
- **Native currency in COMP**: non-US revenue displays in native currency, not USD-converted
- **Bank / financial sector IS**: banks (e.g. HK-listed Chinese banks) use a different income statement structure — no Cost of Revenue, Gross Profit, Operating Income, or EBITDA. These fields show N/A. Net Interest Income and other bank-specific line items are not currently mapped.
- **Semi-annual reporters**: companies that publish only H1 and annual results (e.g. Lenovo 00992 HK) will show data only for Q2 and the annual column in the XLSX download. Q1, Q3, Q4 cells are blank — this reflects the company's actual reporting cadence, not a data gap.
- **Quarterly data availability**: yfinance may not capture the most recent quarterly interim report for some non-US tickers (observed: Q3 2025 missing for China Construction Bank 00939 HK). Data appears once yfinance ingests the filing.

**DCF Valuation**
- **Beta relevering**: uses raw yfinance beta (already levered); Damodaran unlevered/relevered beta is not applied
- **Non-US tickers**: CRP is added to ERP, but the risk-free rate stays US 10Y Treasury — a local sovereign yield would be more appropriate
- **Cyclical / loss-making companies**: negative historical FCFF (e.g. companies with large restructuring charges) propagates into projections; treat the output as directional only
- **GAAP only**: no non-GAAP adjustments — stock-based compensation, restructuring costs, and acquired-intangible amortisation are not stripped out
- **Data source fallback**: if the US Treasury or Damodaran fetch fails, hardcoded constants are used (Rf = 4.3%, ERP = 4.46%); a footnote appears in the KPI strip

**FX**
- **FRD forward rates**: computed from hardcoded approximate benchmark rates, not live OIS/SOFR swap points — directionally correct but not trading-grade
- **FXCA cross rates**: routes through USD when a direct yfinance pair is unavailable; minor rounding on exotic crosses

