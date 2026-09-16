"""
FastAPI web server for Mini-Bloomberg.

Bridges the existing CLI/function layer to a REST API consumed by index.html.

Run with:
    cd /path/to/MINIBB
    uvicorn src.mini_bloomberg.web.server:app --reload --port 8000

Or (if installed as package):
    uvicorn mini_bloomberg.web.server:app --reload --port 8000
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Mini-Bloomberg Web API", version="0.1.0")

# Allow all origins during development (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_web_ui_cache(request, call_next):
    """Keep the single-page UI fresh while the local server is under development."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Serve the web UI at /
_WEB_DIR = Path(__file__).parent / "static"
if _WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_WEB_DIR)), name="static")

# ── Lazy imports (avoid import errors if deps not installed) ───────────────────

def _get_session():
    from mini_bloomberg.core.session import session
    return session


def _get_registry():
    from mini_bloomberg.functions.alpha import ALPHA
    from mini_bloomberg.functions.des  import DES
    from mini_bloomberg.functions.fa   import FA
    from mini_bloomberg.functions.gp   import GP
    from mini_bloomberg.functions.anr  import ANR
    from mini_bloomberg.functions.comp import COMP
    from mini_bloomberg.functions.rpt  import RPT
    from mini_bloomberg.functions.rv   import RV
    from mini_bloomberg.functions.news import NEWS
    from mini_bloomberg.functions.dcf  import DCF
    from mini_bloomberg.functions.qtr  import QTR
    from mini_bloomberg.functions.fxip import FXIP
    from mini_bloomberg.functions.fxca import FXCA
    from mini_bloomberg.functions.fxhv import FXHV
    from mini_bloomberg.functions.frd  import FRD
    from mini_bloomberg.functions.wcr  import WCR
    return {
        "ALPHA": ALPHA, "DES": DES, "FA": FA, "GP": GP, "ANR": ANR,
        "COMP": COMP, "RPT": RPT, "RV": RV,
        "NEWS": NEWS, "DCF": DCF, "QTR": QTR,
        "FXIP": FXIP, "FXCA": FXCA, "FXHV": FXHV, "FRD": FRD, "WCR": WCR,
    }


_ASSET_CLASSES = {"EQUITY", "BOND", "COMDTY", "CURNCY", "INDEX"}
_STR_FLAGS = {
    "base": "base", "quote": "quote", "pair": "pair",
    "from": "from_ccy", "from-ccy": "from_ccy",
    "to": "to_ccy", "to-ccy": "to_ccy",
    "group": "group", "sort-by": "sort_by", "sortby": "sort_by",
    "statement": "statement", "stmt": "statement",
}


# ── Request / response models ──────────────────────────────────────────────────

class CommandRequest(BaseModel):
    command: str


class AgentRequest(BaseModel):
    query: str
    history: list[dict] = []
    ticker: str | None = None


# ── Normalise & parse (mirrors cli/dispatcher.py) ─────────────────────────────

def _normalise(raw: str) -> str:
    s = raw.strip()
    if s.upper().endswith("<GO>"):
        s = s[:-4].strip()
    elif s.upper().endswith("GO") and len(s) > 2 and s[-3] == " ":
        s = s[:-2].strip()
    return s


def _looks_like_ticker(tokens: list[str]) -> bool:
    if not tokens:
        return False
    if len(tokens) >= 2 and tokens[-1].upper() in _ASSET_CLASSES:
        return True
    if len(tokens) == 1:
        t = tokens[0]
        return t.isalnum() and t.isupper() and 1 <= len(t) <= 6
    return False


def _parse_kwargs(cmd: str, args: list[str]) -> dict:
    """Parse optional ticker + flag args into a kwargs dict."""
    if cmd.upper() == "ALPHA":
        from mini_bloomberg.functions.alpha import parse_alpha_args
        return parse_alpha_args(args)
    kwargs: dict = {}
    from mini_bloomberg.core.ticker import parse_ticker
    from mini_bloomberg.core.errors import TickerError

    if args and not args[0].startswith("-"):
        ticker_parts, remaining = [], []
        for i, tok in enumerate(args):
            if tok.startswith("-"):
                remaining = args[i:]
                break
            ticker_parts.append(tok)
        else:
            remaining = []

        if ticker_parts:
            candidate = " ".join(ticker_parts)
            try:
                parse_ticker(candidate)
                kwargs["ticker"] = candidate
                args = remaining
            except TickerError:
                args = ticker_parts + remaining

    i = 0
    while i < len(args):
        tok = args[i].lstrip("-").lower()
        if tok in ("days", "d") and i + 1 < len(args):
            try:
                kwargs["days"] = int(args[i + 1]); i += 2; continue
            except ValueError:
                pass
        if tok in ("years", "y") and i + 1 < len(args):
            try:
                kwargs["years"] = int(args[i + 1]); i += 2; continue
            except ValueError:
                pass
        if tok in ("limit", "n") and i + 1 < len(args):
            try:
                kwargs["limit"] = int(args[i + 1]); i += 2; continue
            except ValueError:
                pass
        if tok in ("quarters", "q") and i + 1 < len(args):
            try:
                kwargs["quarters"] = int(args[i + 1]); i += 2; continue
            except ValueError:
                pass
        if tok == "amount" and i + 1 < len(args):
            try:
                kwargs["amount"] = float(args[i + 1]); i += 2; continue
            except ValueError:
                pass
        if tok in _STR_FLAGS and i + 1 < len(args):
            kwargs[_STR_FLAGS[tok]] = args[i + 1]; i += 2; continue
        i += 1

    return kwargs


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_ui():
    """Serve the web UI. Looks for index.html next to this file or in static/."""
    candidates = [
        Path(__file__).parent / "static" / "index.html",
        Path(__file__).parent / "index.html",
    ]
    for p in candidates:
        if p.exists():
            return FileResponse(str(p))
    return HTMLResponse(
        "<h1>Mini-Bloomberg</h1>"
        "<p>Place <code>index.html</code> in <code>src/mini_bloomberg/web/static/</code>.</p>",
        status_code=200,
    )


@app.get("/api/securities/search")
async def search_securities(q: str = "", limit: int = 8):
    """Search listed mainland-China equities for command-bar autocomplete."""
    query = q.strip()
    if not query:
        return {"status": "ok", "items": []}
    try:
        from starlette.concurrency import run_in_threadpool
        from mini_bloomberg.data.providers.tushare_provider import search_securities as _search
        items = await run_in_threadpool(_search, query, max(1, min(limit, 20)))
        return {"status": "ok", "items": items, "provider": "Tushare Pro"}
    except Exception as exc:
        return {"status": "error", "items": [], "message": str(exc)}


@app.post("/api/command")
async def run_command(req: CommandRequest):
    """
    Execute a Mini-Bloomberg command and return structured JSON.

    Handles:
    - Ticker loading: "AAPL US Equity"
    - Bloomberg functions: DES, FA, GP, ANR, COMP, RPT, RV, FXIP, FXCA, FXHV, FRD, WCR
    - HELP
    """
    line = _normalise(req.command)
    if not line:
        return {"status": "ok", "message": "Empty command"}

    upper = line.upper()
    tokens = line.split()
    cmd = tokens[0].upper()

    if upper in ("QUIT", "EXIT", "Q"):
        return {"status": "ok", "message": "Cannot quit from web UI."}

    if upper == "HELP":
        return {"status": "ok", "type": "help"}

    try:
        registry = _get_registry()
        session = _get_session()
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Mini-Bloomberg package not installed: {e}. "
                   "Run: pip install -e . inside the MINIBB directory.",
        )

    # ── Agent query (?...) ─────────────────────────────────────────────────────
    if line.startswith("?"):
        query = line[1:].strip()
        return await run_agent(AgentRequest(query=query, ticker=str(session.loaded_ticker) if session.is_loaded else None))

    # ── Bloomberg function ─────────────────────────────────────────────────────
    if cmd in registry:
        kwargs = _parse_kwargs(cmd, tokens[1:])
        fn_class = registry[cmd]
        try:
            if cmd == "ALPHA":
                from starlette.concurrency import run_in_threadpool
                result = await run_in_threadpool(fn_class().run, **kwargs)
            else:
                result = fn_class().run(**kwargs)
            response: dict[str, Any] = dict(result)
            response["provider"] = "Local factor engine" if cmd == "ALPHA" else (
                "Tushare Pro" if session.is_loaded and session.loaded_ticker.is_china else "FMP/OpenBB"
            )
            if cmd == "ALPHA" and result.get("data", {}).get("sources"):
                response["provider"] = ", ".join(sorted({row["source"] for row in result["data"]["sources"]}))
            if session.is_loaded:
                response["loaded_ticker"] = str(session.loaded_ticker)

            # For RPT: embed the HTML in the response
            if cmd == "RPT" and result.get("status") == "ok":
                try:
                    from mini_bloomberg.render.html_renderer import render_report_html
                    html_path = render_report_html(result)
                    response["rpt_html"] = html_path.read_text(encoding="utf-8")
                except Exception as rpt_err:
                    response["rpt_error"] = str(rpt_err)

            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ── Load security ──────────────────────────────────────────────────────────
    if _looks_like_ticker(tokens):
        try:
            from mini_bloomberg.core.ticker import parse_ticker
            from mini_bloomberg.core.errors import TickerError
            t = session.load(line)
            # Also auto-run DES to show details
            try:
                des_result = registry["DES"]().run()
                return {
                    "status": "ok",
                    "loaded_ticker": str(t),
                    "message": f"Loaded: {t}",
                    **des_result,
                }
            except Exception:
                return {"status": "ok", "loaded_ticker": str(t), "message": f"Loaded: {t}"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    raise HTTPException(
        status_code=400,
        detail=f"Unknown command '{cmd}'. Type HELP for available commands.",
    )


@app.post("/api/agent")
async def run_agent(req: AgentRequest):
    """
    Run the Claude AI agent for natural-language queries.
    Streams tool calls and returns the final response.
    """
    try:
        from mini_bloomberg.agents.orchestrator import run_agent as _run_agent
        from mini_bloomberg.agents.prompts import ANALYST_SYSTEM_PROMPT
        from mini_bloomberg.agents.tools import ALL_TOOLS, FUNCTIONS_BY_NAME
        from mini_bloomberg.config import get_settings
        import anthropic
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Agent dependencies not available: {e}")

    settings = get_settings()
    from mini_bloomberg.core.llm import _get_client
    client = _get_client()
    model = settings.claude_model

    # Build message history
    messages: list[dict] = list(req.history)
    query = req.query
    if req.ticker:
        query = f"[Loaded security: {req.ticker}] {query}"
    messages.append({"role": "user", "content": query})

    tool_calls_log: list[str] = []
    full_text = ""

    system = [
        {
            "type": "text",
            "text": ANALYST_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    max_rounds = 6
    for _ in range(max_rounds):
        response = client.messages.create(
            model=model,
            system=system,
            tools=ALL_TOOLS,
            messages=messages,
            max_tokens=4096,
        )

        # Collect text
        for block in response.content:
            if hasattr(block, "text"):
                full_text += block.text

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_use_blocks:
            break

        # Run tools
        def _run_tool(tu):
            fn = FUNCTIONS_BY_NAME.get(tu.name)
            if fn is None:
                return {"type": "tool_result", "tool_use_id": tu.id,
                        "content": json.dumps({"error": f"Unknown tool: {tu.name}"})}
            try:
                result = json.dumps(fn.run(**tu.input))
            except Exception as e:
                result = json.dumps({"error": str(e)})
            return {"type": "tool_result", "tool_use_id": tu.id, "content": result}

        results = [None] * len(tool_use_blocks)
        threads = []
        for i, tu in enumerate(tool_use_blocks):
            tool_calls_log.append(f"{tu.name}({json.dumps(tu.input)[:80]})")
            def worker(idx, t):
                results[idx] = _run_tool(t)
            th = threading.Thread(target=worker, args=(i, tu))
            threads.append(th)
            th.start()
        for th in threads:
            th.join()

        messages.append({"role": "user", "content": results})

    return {
        "status": "ok",
        "response": full_text.strip() or "(no response)",
        "tool_calls": tool_calls_log,
    }


@app.get("/api/status")
async def status():
    """Health check & session state."""
    try:
        session = _get_session()
        return {
            "status": "ok",
            "loaded_ticker": str(session.loaded_ticker) if session.is_loaded else None,
            "version": "0.1.0",
        }
    except ImportError:
        return {"status": "degraded", "message": "mini_bloomberg package not found"}
