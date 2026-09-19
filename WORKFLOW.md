# End-to-End Workflow

This document explains the **complete data journey** in ALPHADESK: where data comes from, how it's processed, and how it reaches the user's screen. Read this first to understand the architecture before any code.

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER TYPES COMMAND                          │
│                       "AAPL US Equity <GO>"                          │
│                            "DES <GO>"                                │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1: CLI / REPL (prompt-toolkit + typer)                       │
│  • Reads keystrokes                                                  │
│  • Parses command ("DES" vs "? query" vs "<TICKER> <GO>")           │
│  • Updates session state                                             │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 2: FUNCTION DISPATCHER                                        │
│  • Looks up "DES" → DES() function class                            │
│  • Calls .run(ticker="AAPL US Equity")                              │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 3: BLOOMBERG FUNCTION (functions/des.py)                     │
│  • Asks data layer for company profile                              │
│  • Formats into structured dict                                     │
│  • Returns {"status": "ok", "data": {...}}                          │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 4: DATA LAYER (data/equity_profile.py)                       │
│  • Checks cache (diskcache) → if hit, return                        │
│  • Routes by exchange: US → FMP, non-US → OpenBB                    │
│  • Calls provider, validates with Pydantic, caches, returns         │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 5: EXTERNAL APIs                                              │
│  • FMP REST API (financialmodelingprep.com)                         │
│  • OpenBB Platform (openbb.co) — wraps yfinance, polygon, etc.      │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
                        [Data flows back up]
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 6: RENDERER (render/cli_renderer.py)                          │
│  • Takes structured dict                                            │
│  • Formats with Rich: colored panels, tables, ASCII charts          │
│  • Prints to terminal                                               │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
                        [User sees Bloomberg-style output]
```

Every layer has ONE job. Never mix them.

---

## Path A: Direct Command (`DES <GO>`)

**What happens when the user types `DES <GO>` with `AAPL US Equity` loaded:**

1. **REPL** captures input → dispatches to function router
2. **Dispatcher** finds `DES` in the function registry, calls `DES().run(ticker="AAPL US Equity")`
3. **DES function** parses ticker → `Ticker(symbol="AAPL", exchange="US", asset_class="Equity")`
4. **DES function** calls `data.equity_profile.get_profile(ticker)`
5. **Data layer** checks cache. Cache miss → routes to FMP (because US exchange)
6. **FMP provider** hits `https://financialmodelingprep.com/api/v3/profile/AAPL` with API key
7. **FMP provider** receives JSON, validates into `CompanyProfile` Pydantic model, returns
8. **Data layer** caches result (24h TTL), returns `CompanyProfile` up the stack
9. **DES function** dumps model to dict, wraps in `{"status": "ok", "data": {...}}`
10. **Renderer** receives dict, creates a Rich Panel with company name, sector, market cap
11. **Terminal** prints the panel. User sees Bloomberg-style output.

**Key insight**: step 7 is the only place where raw API data becomes a typed Python object. From that point on, everything is validated.

---

## Path B: Agent Command (`? compare NVDA and AMD <GO>`)

**What happens when the user asks a natural-language question:**

1. **REPL** sees `?` prefix → dispatches to agent instead of function router
2. **Agent orchestrator** packages the query for Claude:
   ```python
   client.messages.create(
       model="claude-opus-4-5",
       system="You are a junior equity analyst...",
       tools=[des_schema, fa_schema, gp_schema, anr_schema, comp_schema],
       messages=[{"role": "user", "content": "compare NVDA and AMD"}]
   )
   ```
3. **Claude API** returns: "I'll call FA for NVDA and FA for AMD" → `tool_use` blocks
4. **Orchestrator** executes tools:
   - Calls `FA().run(ticker="NVDA US Equity")` — same exact code as Path A
   - Calls `FA().run(ticker="AMD US Equity")`
5. **Orchestrator** sends tool results back to Claude as `tool_result` blocks
6. **Claude** either asks for more tools (loop) OR returns final text answer
7. **Renderer** prints Claude's answer with a distinctive style (e.g., blue panel, "AI" label)

**Key insight**: the agent and the CLI both call the same `FA().run()`. Zero code duplication. That's the whole architectural payoff.

---

## Data Sources: Who Does What

| Data Type | US Tickers | Non-US Tickers | Fallback |
|---|---|---|---|
| Company profile (DES) | FMP `/profile` | OpenBB `equity.profile` | Swap providers |
| Financials (FA) | FMP `/income-statement`, `/balance-sheet-statement`, `/cash-flow-statement` | OpenBB `equity.fundamental.*` | Swap providers |
| Price history (GP) | FMP `/historical-price-full` | OpenBB `equity.price.historical` | yfinance via OpenBB |
| Analyst ratings (ANR) | FMP `/analyst-stock-recommendations` + `/price-target-consensus` | OpenBB `equity.estimates.consensus` | Swap providers |
| Peers (COMP) | FMP `/stock_peers` then loop `/profile` for each | OpenBB `equity.compare.peers` | Swap providers |

**Why this split?** FMP has best-in-class US fundamentals with a generous free tier (250 calls/day). OpenBB is a meta-provider that aggregates multiple sources for international coverage. Neither alone covers global equity well — together they do.

---

## UI: What Tools, What Each Does

You're building a CLI. Here are the five tools doing the UI work:

### 1. `typer` — Command-line entry point
Defines `mini-bb` as an installable CLI command. One tiny file (`cli/app.py`).

```python
import typer
app = typer.Typer()

@app.command()
def main():
    """Launch the ALPHADESK REPL."""
    from .repl import run_repl
    run_repl()
```

### 2. `prompt-toolkit` — The REPL input loop
This is what makes it feel like a real terminal:
- Command history (up/down arrow)
- Tab autocompletion (suggest function names)
- Multi-line input handling
- Custom keybindings (`<GO>` mapped to Enter)

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

completer = WordCompleter(["DES", "FA", "GP", "ANR", "COMP", "HELP", "QUIT"])
session = PromptSession(completer=completer)

while True:
    user_input = session.prompt("ALPHADESK> ")
    # ... dispatch
```

### 3. `rich` — All visual output
Every piece of formatted text goes through Rich:
- **Tables** for financial statements (FA), comparables (COMP), analyst ratings (ANR)
- **Panels** for company descriptions (DES) — bordered boxes with title
- **Columns** for side-by-side layouts
- **Status bar** at the bottom showing loaded ticker and time
- **Colored text** — yellow prompts, green values, red for negatives

```python
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

table = Table(title="Apple Inc — Income Statement")
table.add_column("Year")
table.add_column("Revenue", justify="right")
table.add_column("Net Income", justify="right")
table.add_row("2024", "$391.0B", "$97.0B")
console.print(table)
```

### 4. `plotext` — ASCII price charts in the terminal
This is what makes `GP` look impressive. Real candlestick charts rendered in Unicode.

```python
import plotext as plt
plt.candlestick(dates, ohlc_data)
plt.title("AAPL — 1 Year")
plt.show()
```

### 5. `pydantic` — Not visual, but keeps everything sane
Every data object is a Pydantic model. When the LLM gets a tool result, it gets a clean JSON schema. When the renderer gets a result, it knows the exact fields available. No `KeyError`, no guessing.

---

## The Bloomberg Look & Feel

What actually makes this feel like a Bloomberg Terminal:

| Bloomberg feature | Our implementation |
|---|---|
| Yellow prompt, green/black theme | Rich styles: `Style(color="bright_green", bgcolor="black")` + yellow prompt |
| Load security, then run functions | `core/session.py` holds currently-loaded ticker |
| `<GO>` to execute | Map Enter key in prompt-toolkit |
| UPPERCASE commands | Dispatcher uppercases input before lookup |
| Status bar | Rich's `Layout` with a footer showing ticker + time |
| Function codes (DES, FA, GP…) | Literally the names of our function classes |
| Help menu | `HELP <GO>` prints a Rich table of all commands |

---

## Caching Strategy

Without caching, development is painful. With `diskcache`, it's instant.

**Rule**: Every data-layer function is decorated with cache. 24-hour TTL during development.

```python
from mini_bloomberg.core.cache import cached

@cached(ttl=86400)  # 24 hours
def get_profile(ticker: Ticker) -> CompanyProfile:
    # ... API call
```

**What to cache**: everything from external APIs.
**What NOT to cache**: session state, LLM responses, rendered output.

---

## Error Handling Strategy

At every layer, errors return structured objects, never raw exceptions:

```python
# Data layer
try:
    profile = fmp.get_profile(ticker)
except (RateLimitError, TimeoutError):
    profile = openbb.get_profile(ticker)  # fallback
except InvalidTickerError:
    raise DataSourceError(f"No data for {ticker}")

# Function layer
def run(self, ticker: str) -> dict:
    try:
        profile = get_profile(parse_ticker(ticker))
        return {"status": "ok", "data": profile.model_dump()}
    except DataSourceError as e:
        return {"status": "error", "message": str(e)}

# Renderer
if result["status"] == "error":
    console.print(f"[red]ERROR:[/red] {result['message']}")
else:
    render_profile_panel(result["data"])

# Agent
# Claude sees the error dict as tool result — it can reason about it,
# apologize to the user, suggest alternatives
```

This is why a failed API call never crashes the terminal and why the LLM agent gracefully handles missing data.

---

## Session State: The "Loaded Security"

Real Bloomberg has a loaded-security concept: you type `AAPL US Equity <GO>`, then subsequent commands (`DES`, `FA`) run against AAPL. Ours works the same way.

```python
# core/session.py
class Session:
    loaded_ticker: Ticker | None = None

    def load(self, ticker_str: str):
        self.loaded_ticker = parse_ticker(ticker_str)

    def require_loaded(self) -> Ticker:
        if self.loaded_ticker is None:
            raise NoLoadedSecurityError("Load a security first: e.g. 'AAPL US Equity <GO>'")
        return self.loaded_ticker

session = Session()  # module-level singleton
```

Functions pull from session when called without an explicit ticker:

```python
# DES called with no args → use session
# DES called with ticker arg → use that (this is how the agent calls it)
def run(self, ticker: str | None = None) -> dict:
    t = parse_ticker(ticker) if ticker else session.require_loaded()
    # ...
```

---

## Summary: What Each File Does

| File | Role | Talks to |
|---|---|---|
| `cli/app.py` | Typer entry point, launches REPL | `cli/repl.py` |
| `cli/repl.py` | prompt-toolkit loop | `cli/dispatcher.py` |
| `cli/dispatcher.py` | Parses commands, routes to functions or agent | `functions/*`, `agents/orchestrator.py` |
| `core/session.py` | Holds loaded ticker | Everything |
| `core/ticker.py` | Parses Bloomberg ticker strings | — |
| `core/cache.py` | Disk cache decorator | — |
| `data/schemas.py` | Pydantic models | — |
| `data/providers/fmp_provider.py` | FMP API wrapper | FMP REST API |
| `data/providers/openbb_provider.py` | OpenBB wrapper | OpenBB Platform |
| `data/equity_*.py` | Provider routers (choose FMP vs OpenBB) | `providers/*` |
| `functions/base.py` | ABC for all functions | — |
| `functions/des.py`, `fa.py`, etc. | One file per Bloomberg function | `data/*`, returns dicts |
| `render/cli_renderer.py` | Rich tables/panels/charts | Only the CLI uses this |
| `render/json_renderer.py` | Clean JSON for LLM | Only the agent uses this |
| `agents/tools.py` | Auto-generates Anthropic tool specs | Reads from `functions/*.tool_schema()` |
| `agents/orchestrator.py` | Tool-use loop with Claude | `anthropic` SDK, `functions/*` |
| `agents/prompts.py` | System prompts | — |
