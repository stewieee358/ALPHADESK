"""
Dispatcher: parse a raw input line and route to the right handler.

Rules:
  "AAPL US Equity <GO>"  → load security into session
  "DES <GO>"             → run Bloomberg function
  "? <query> <GO>"       → run LLM agent
  "HELP <GO>"            → print help table
  "QUIT <GO>" / "EXIT"   → exit REPL
  "<GO>" alone           → re-run last command (not implemented in v1, ignored)

Input is normalised: strip whitespace, strip trailing "<GO>" / "GO", uppercase.
"""

from mini_bloomberg.core.errors import MiniBloombergError, NoLoadedSecurityError, TickerError
from mini_bloomberg.core.session import session
from mini_bloomberg.core.ticker import parse_ticker
from mini_bloomberg.render.cli_renderer import (
    console, render_anr, render_comp, render_des, render_fa, render_gp,
    render_rpt, render_rv, render_news, render_dcf, render_qtr,
    render_fxip, render_fxca, render_fxhv, render_frd, render_wcr,
    render_error, render_loaded, render_status, ORANGE, HEADER, DIM, GREEN,
)

from rich.table import Table
from rich.panel import Panel

# ── Function registry ──────────────────────────────────────────────────────────

def _registry():
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

from mini_bloomberg.render.factor_renderer import render_alpha

RENDERERS = {
    "ALPHA": render_alpha,
    "DES":  render_des,
    "FA":   render_fa,
    "GP":   render_gp,
    "ANR":  render_anr,
    "COMP": render_comp,
    "RPT":  render_rpt,
    "RV":   render_rv,
    "NEWS": render_news,
    "DCF":  render_dcf,
    "QTR":  render_qtr,
    "FXIP": render_fxip,
    "FXCA": render_fxca,
    "FXHV": render_fxhv,
    "FRD":  render_frd,
    "WCR":  render_wcr,
}

ASSET_CLASSES = {"EQUITY", "BOND", "COMDTY", "CURNCY", "INDEX"}


# ── Normalise input ────────────────────────────────────────────────────────────

def _normalise(raw: str) -> str:
    """Strip trailing <GO> / GO and extra whitespace."""
    s = raw.strip()
    if s.upper().endswith("<GO>"):
        s = s[:-4].strip()
    elif s.upper().endswith("GO"):
        # only strip bare "GO" if preceded by whitespace
        if len(s) > 2 and s[-3] == " ":
            s = s[:-2].strip()
    return s


# ── Ticker detection ───────────────────────────────────────────────────────────

def _looks_like_ticker(tokens: list[str]) -> bool:
    """
    Heuristic: 2–3 tokens where the last is an asset class keyword,
    or a single token that is 1–5 uppercase letters/digits with no spaces.
    """
    if not tokens:
        return False
    if len(tokens) >= 2 and tokens[-1].upper() in ASSET_CLASSES:
        return True
    if len(tokens) == 1:
        t = tokens[0]
        return t.isalnum() and t.isupper() and 1 <= len(t) <= 6
    return False


# ── Main dispatch ──────────────────────────────────────────────────────────────

def dispatch(raw: str) -> bool:
    """
    Process one input line. Returns False if the REPL should exit, True otherwise.
    """
    line = _normalise(raw)
    if not line:
        return True

    upper = line.upper()

    # ── Exit ─────────────────────────────────────────────────────────────────
    if upper in ("QUIT", "EXIT", "Q"):
        console.print(f"[{DIM}]Goodbye.[/{DIM}]")
        return False

    # ── Help ─────────────────────────────────────────────────────────────────
    if upper == "HELP":
        _render_help()
        return True

    # ── Clear agent memory ────────────────────────────────────────────────────
    if upper in ("CLEAR HISTORY", "CLEAR"):
        from mini_bloomberg.agents.orchestrator import clear_history
        clear_history()
        console.print(f"[{DIM}]Conversation history cleared.[/{DIM}]")
        return True

    # ── Agent mode: "? <query>" ───────────────────────────────────────────────
    if line.startswith("?"):
        query = line[1:].strip()
        if not query:
            render_error("Usage: ? <your question>  e.g. ? compare NVDA and AMD margins")
            return True
        _run_agent(query)
        return True

    # ── Bloomberg function: "DES", "FA 4", "GP --days 90" etc. ───────────────
    tokens = line.split()
    cmd = tokens[0].upper()
    registry = _registry()

    if cmd in registry:
        kwargs = _parse_function_kwargs(cmd, tokens[1:])
        fn_class = registry[cmd]
        renderer = RENDERERS[cmd]
        try:
            result = fn_class().run(**kwargs)
            renderer(result)
        except NoLoadedSecurityError as e:
            render_error(str(e))
        except Exception as e:
            render_error(f"Unexpected error running {cmd}: {e}")
        return True

    # ── Load security: "AAPL US Equity" ──────────────────────────────────────
    if _looks_like_ticker(tokens):
        try:
            t = session.load(line)
            render_loaded(str(t))
        except TickerError as e:
            render_error(str(e))
        return True

    # ── Unknown ───────────────────────────────────────────────────────────────
    render_error(
        f"Unknown command '{cmd}'. "
        "Type HELP <GO> for available commands, or load a ticker first."
    )
    return True


def _parse_function_kwargs(cmd: str, args: list[str]) -> dict:
    """
    Extract optional ticker and numeric params from remaining tokens.

    E.g. "FA AAPL US Equity" → {ticker: "AAPL US Equity"}
         "GP --days 90"      → {days: 90}
         "DES"               → {}  (uses session)

    FX functions (FXHV, FXCA, FXIP, WCR, FRD) accept positional currency tokens
    which are passed through as a joined "ticker" string for their own parsers:
         "FXHV EUR USD"      → {ticker: "EUR USD"}
         "FXCA USD JPY 1000" → {ticker: "USD JPY 1000"}
         "FXIP em EUR"       → {ticker: "em EUR"}
         "WCR g10 JPY 1m"    → {ticker: "g10 JPY 1m"}
         "FRD EURUSD"        → {ticker: "EURUSD"}   (existing behaviour)
    """
    if cmd.upper() == "ALPHA":
        from mini_bloomberg.functions.alpha import parse_alpha_args
        return parse_alpha_args(args)
    kwargs: dict = {}

    # Commands whose positional args are NOT Bloomberg security tickers but
    # currency codes / group keywords.  Pass them straight through as `ticker`.
    _FX_POSITIONAL_CMDS = {"FXHV", "FXCA", "FXIP", "WCR", "FRD"}

    if cmd.upper() in _FX_POSITIONAL_CMDS:
        # Split into positional tokens (before any --flag) and flag args
        positional = []
        remaining  = []
        for i, token in enumerate(args):
            if token.startswith("-"):
                remaining = args[i:]
                break
            positional.append(token)
        else:
            remaining = []

        if positional:
            kwargs["ticker"] = " ".join(positional)
        args = remaining

    else:
        # Standard equity-ticker detection for all other commands
        if args and not args[0].startswith("-"):
            ticker_parts = []
            remaining = []
            for i, token in enumerate(args):
                if token.startswith("-"):
                    remaining = args[i:]
                    break
                ticker_parts.append(token)
            else:
                remaining = []

            if ticker_parts:
                candidate = " ".join(ticker_parts)
                try:
                    parse_ticker(candidate)
                    kwargs["ticker"] = candidate
                    args = remaining
                except TickerError:
                    args = ticker_parts + remaining  # put back, not a ticker

    # Parse --days / --years / --amount / FX string flags
    _STR_FLAGS = {
        "base":     "base",
        "quote":    "quote",
        "pair":     "pair",
        "from":     "from_ccy",
        "from-ccy": "from_ccy",
        "to":       "to_ccy",
        "to-ccy":   "to_ccy",
        "group":     "group",
        "sort-by":   "sort_by",
        "sortby":    "sort_by",
        "statement": "statement",
        "stmt":      "statement",
    }
    i = 0
    while i < len(args):
        tok = args[i].lstrip("-").lower()
        if tok in ("days", "d") and i + 1 < len(args):
            try:
                kwargs["days"] = int(args[i + 1])
                i += 2
                continue
            except ValueError:
                pass
        if tok in ("years", "y") and i + 1 < len(args):
            try:
                kwargs["years"] = int(args[i + 1])
                i += 2
                continue
            except ValueError:
                pass
        if tok in ("limit", "n") and i + 1 < len(args):
            try:
                kwargs["limit"] = int(args[i + 1])
                i += 2
                continue
            except ValueError:
                pass
        if tok in ("quarters", "q") and i + 1 < len(args):
            try:
                kwargs["quarters"] = int(args[i + 1])
                i += 2
                continue
            except ValueError:
                pass
        if tok == "amount" and i + 1 < len(args):
            try:
                kwargs["amount"] = float(args[i + 1])
                i += 2
                continue
            except ValueError:
                pass
        if tok in _STR_FLAGS and i + 1 < len(args):
            kwargs[_STR_FLAGS[tok]] = args[i + 1]
            i += 2
            continue
        i += 1

    return kwargs


def _render_help() -> None:
    t = Table(border_style="dim", header_style=HEADER, show_lines=False, expand=False)
    t.add_column("Command",     style=ORANGE, min_width=16, no_wrap=True)
    t.add_column("Description", style=DIM,    min_width=42)
    t.add_column("Example",     style=GREEN,  min_width=24, no_wrap=True)

    rows = [
        ("<TICKER> <GO>", "Load a security into the session",          "AAPL US Equity <GO>"),
        ("DES <GO>",      "Company description and key stats",         "DES <GO>"),
        ("FA <GO>",       "Financial analysis (income/balance/CF)",    "FA <GO>"),
        ("GP <GO>",       "ASCII price chart (default 1 year)",        "GP --days 90 <GO>"),
        ("ANR <GO>",      "Analyst ratings and price targets",         "ANR <GO>"),
        ("COMP <GO>",     "Comparable companies side-by-side",         "COMP <GO>"),
        ("RPT <GO>",      "Full equity report + Markdown file",        "RPT <GO>"),
        ("RV <GO>",       "Relative value vs. peers",                  "RV <GO>"),
        ("NEWS <GO>",     "Recent company headlines",                  "NEWS --limit 20 <GO>"),
        ("DCF <GO>",      "Discounted cash flow fair value",           "DCF <GO>"),
        ("QTR <GO>",      "Quarterly financials (IS/BS/CF)",           "QTR --quarters 12 <GO>"),
        ("FXIP [grp] [ccy] <GO>",  "FX spot monitor: G10/EM vs quote",        "FXIP em EUR <GO>"),
        ("FXCA [ccy ccy] [amt] <GO>", "FX calculator: convert amount",        "FXCA USD JPY 1000 <GO>"),
        ("FXHV [ccy ccy] <GO>",    "FX historical volatility (multi-window)", "FXHV EUR USD <GO>"),
        ("FRD [ccy ccy] <GO>",     "FX forward rate curve (CIP-implied)",     "FRD USD EUR <GO>"),
        ("WCR [grp] [ccy] [hz] <GO>", "World currency ranker by performance", "WCR em EUR 1m <GO>"),
        ("? <query>",          "Ask the AI analyst a question",        "? compare NVDA AMD <GO>"),
        ("CLEAR HISTORY <GO>", "Wipe AI analyst conversation memory",  "CLEAR HISTORY <GO>"),
        ("HELP <GO>",          "Show this help screen",                "HELP <GO>"),
        ("QUIT <GO>",          "Exit ALPHADESK",                  "QUIT <GO>"),
    ]
    for row in rows:
        t.add_row(*row)

    console.print()
    console.print(Panel(
        t,
        title=f"[{ORANGE}]HELP[/{ORANGE}]  [{HEADER}]ALPHADESK Commands[/{HEADER}]",
        border_style="yellow",
        padding=(1, 2),
    ))
    console.print()


def _run_agent(query: str) -> None:
    try:
        from mini_bloomberg.agents.orchestrator import run_agent
        run_agent(query)
    except ImportError:
        render_error("Agent not yet implemented (Milestone 6).")
    except Exception as e:
        render_error(f"Agent error: {e}")
