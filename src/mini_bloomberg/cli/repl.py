"""
Interactive REPL powered by prompt-toolkit.
Bloomberg-style UX: yellow prompt, green/black theme, tab-complete, history.
"""

import sys
from datetime import datetime
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from mini_bloomberg.cli.dispatcher import dispatch
from mini_bloomberg.core.session import session
from mini_bloomberg.render.cli_renderer import console, ORANGE, DIM, GREEN, HEADER

# ── Prompt-toolkit style ───────────────────────────────────────────────────────

PT_STYLE = Style.from_dict({
    "prompt":         "#ffaf00 bold",   # amber — Bloomberg yellow
    "ticker":         "#00ff00",        # bright green
    "rprompt":        "#444444",        # dim right-side status
})

# ── Tab completions ────────────────────────────────────────────────────────────

COMPLETIONS = WordCompleter(
    ["DES", "FA", "GP", "ANR", "COMP", "HELP", "QUIT", "EXIT",
     "US Equity", "HK Equity", "JP Equity", "FP Equity", "GR Equity", "LN Equity"],
    ignore_case=True,
    sentence=True,
)

# ── History file ───────────────────────────────────────────────────────────────

_HISTORY_FILE = Path.home() / ".mini_bloomberg_history"


# ── Right-side status (ticker + time) ─────────────────────────────────────────

def _rprompt() -> HTML:
    ticker_str = str(session.loaded_ticker) if session.is_loaded else "No security loaded"
    now = datetime.now().strftime("%H:%M:%S")
    return HTML(f'<rprompt> {ticker_str}  {now} </rprompt>')


def _prompt_text() -> HTML:
    return HTML('<prompt>ALPHADESK&gt; </prompt>')


# ── Banner ────────────────────────────────────────────────────────────────────

def _print_banner() -> None:
    banner = Text()
    banner.append("  ALPHADESK  ", style="bold black on bright_yellow")
    banner.append("  Equity Analysis Terminal  ", style="bold bright_white on black")
    console.print()
    console.print(banner)
    console.print(
        f"  [{DIM}]Type a ticker to load it, then run DES / FA / GP / ANR / COMP.[/{DIM}]\n"
        f"  [{DIM}]Prefix with [/{DIM}][{ORANGE}]?[/{ORANGE}] [{DIM}]to ask the AI analyst. "
        f"[/{DIM}][{ORANGE}]HELP <GO>[/{ORANGE}] [{DIM}]for all commands.[/{DIM}]"
    )
    console.print()


# ── Main REPL loop ────────────────────────────────────────────────────────────

def run_repl() -> None:
    # Force UTF-8 on Windows for Rich + plotext
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    _print_banner()

    ps = PromptSession(
        history=FileHistory(str(_HISTORY_FILE)),
        completer=COMPLETIONS,
        auto_suggest=AutoSuggestFromHistory(),
        style=PT_STYLE,
        mouse_support=False,
        complete_while_typing=True,
    )

    while True:
        try:
            raw = ps.prompt(
                _prompt_text,
                rprompt=_rprompt,
            )
        except KeyboardInterrupt:
            console.print(f"\n[{DIM}](Ctrl-C: type QUIT <GO> to exit)[/{DIM}]")
            continue
        except EOFError:
            console.print(f"[{DIM}]Goodbye.[/{DIM}]")
            break

        if not dispatch(raw):
            break
