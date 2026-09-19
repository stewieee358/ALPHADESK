# ALPHADESK Web UI — Setup Guide

## What's included

| File | Purpose |
|------|---------|
| `index.html` | The web terminal UI (Bloomberg-style dark theme) |
| `server.py` | FastAPI backend that bridges the web UI to your existing mini_bloomberg Python code |

## Quick start

### 1. Copy files into your project

```
MINIBB/
├── src/mini_bloomberg/
│   └── web/
│       ├── __init__.py        ← create empty file
│       ├── server.py          ← copy server.py here
│       └── static/
│           └── index.html     ← copy index.html here
```

```bash
cd MINIBB
mkdir -p src/mini_bloomberg/web/static
cp /path/to/server.py src/mini_bloomberg/web/server.py
cp /path/to/index.html src/mini_bloomberg/web/static/index.html
touch src/mini_bloomberg/web/__init__.py
```

### 2. Install FastAPI dependencies

```bash
pip install fastapi uvicorn[standard]
# or with uv:
uv add fastapi uvicorn
```

### 3. Run the server

```bash
cd MINIBB
uvicorn src.mini_bloomberg.web.server:app --reload --port 8000
```

Then open **http://localhost:8000** in your browser.

### 4. Set your API keys (same as for CLI)

The server uses the same `.env` file as your CLI. Make sure it contains:
```
FMP_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
```

---

## How it works

```
Browser (index.html)
    │
    ├── POST /api/command   → runs DES, FA, GP, ANR, COMP, RPT, RV, FX functions
    │                          returns structured JSON, rendered in the UI
    │
    ├── POST /api/agent     → calls Claude AI agent with tool use
    │                          returns text response + list of tool calls
    │
    └── GET  /api/status    → health check & loaded ticker
```

The backend is a **thin wrapper** around your existing mini_bloomberg functions — no rewriting needed. It reuses:
- `mini_bloomberg.functions.*` — all Bloomberg function classes
- `mini_bloomberg.core.session` — ticker session state
- `mini_bloomberg.agents.orchestrator` — Claude AI agent
- `mini_bloomberg.render.html_renderer` — HTML report generation (for RPT)

---

## Web UI features

### 1. Command bar (top)
- Type Bloomberg-style commands: `AAPL US Equity`, `DES`, `FA`, `GP --days 90`, `ANR`, `COMP`, `RPT`, `FXIP`, etc.
- Autocomplete as you type — press Tab or Arrow keys to navigate
- Press Enter (or append `<GO>`) to execute
- Prefix with `?` to ask the AI agent: `? compare AAPL and MSFT margins`

### 2. Result panel (center)
- **OUTPUT tab**: Rendered results with formatted tables, key-value grids, badges
- **RAW DATA tab**: Full JSON response for debugging
- RPT generates a full investment-bank-style HTML report that renders inline

### 3. AI Agent panel (right)
- Type natural language questions directly in the agent panel
- Or prefix any command bar query with `?`
- Streams tool call logs showing what data the agent fetched
- Maintains conversation history within the session

### Sidebar
- Asset class selector (cosmetic, mirrors Bloomberg layout)
- Function shortcuts — click DES, FA, GP, etc. to fill the command bar
- FX function shortcuts
- Command history

---

## Adding more commands

To add a new function to the web UI, you only need to:
1. Add it to `_get_registry()` in `server.py`
2. Optionally add a custom renderer in `index.html`'s `switch (fnCmd)` block

The generic renderer in `renderGeneric()` will handle any new function automatically.
