"""
Typer entry point. `mini-bb` launches the REPL.
Individual commands (`mini-bb des "AAPL US Equity"`) work for quick testing.
"""

from typing import Optional

import typer

app = typer.Typer(
    name="mini-bb",
    help="ALPHADESK Terminal — equity analysis powered by Claude.",
    add_completion=False,
)


@app.command()
def des(
    ticker: Optional[str] = typer.Argument(None, help="Bloomberg-style ticker, e.g. 'AAPL US Equity'"),
) -> None:
    """Company description: name, sector, exchange, market cap."""
    from mini_bloomberg.functions.des import DES
    from mini_bloomberg.render.cli_renderer import render_des
    render_des(DES().run(ticker=ticker))


@app.command()
def fa(
    ticker: Optional[str] = typer.Argument(None, help="Bloomberg-style ticker"),
    years: int = typer.Option(4, "--years", "-y", help="Number of annual periods"),
) -> None:
    """Financial analysis: income statement, balance sheet, cash flow."""
    from mini_bloomberg.functions.fa import FA
    from mini_bloomberg.render.cli_renderer import render_fa
    render_fa(FA().run(ticker=ticker, years=years))


@app.command()
def gp(
    ticker: Optional[str] = typer.Argument(None, help="Bloomberg-style ticker"),
    days: int = typer.Option(365, "--days", "-d", help="Lookback in trading days"),
) -> None:
    """Graph price: ASCII price chart for configurable lookback."""
    from mini_bloomberg.functions.gp import GP
    from mini_bloomberg.render.cli_renderer import render_gp
    render_gp(GP().run(ticker=ticker, days=days))


@app.command()
def anr(
    ticker: Optional[str] = typer.Argument(None, help="Bloomberg-style ticker"),
) -> None:
    """Analyst recommendations: consensus rating and price targets."""
    from mini_bloomberg.functions.anr import ANR
    from mini_bloomberg.render.cli_renderer import render_anr
    render_anr(ANR().run(ticker=ticker))


@app.command()
def comp(
    ticker: Optional[str] = typer.Argument(None, help="Bloomberg-style ticker"),
) -> None:
    """Comparables: side-by-side table of peer companies."""
    from mini_bloomberg.functions.comp import COMP
    from mini_bloomberg.render.cli_renderer import render_comp
    render_comp(COMP().run(ticker=ticker))


@app.callback(invoke_without_command=True)
def _repl_fallback(ctx: typer.Context) -> None:
    """Launch the ALPHADESK REPL when called with no subcommand."""
    if ctx.invoked_subcommand is None:
        from mini_bloomberg.cli.repl import run_repl
        run_repl()


def main() -> None:
    app()
