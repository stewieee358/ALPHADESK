from rich.table import Table
from .cli_renderer import console, render_error


def render_alpha(result):
    if result.get("status") != "ok":
        render_error(result.get("message", "Factor evaluation failed"))
        return
    data = result["data"]
    if data["operators"]:
        console.print(", ".join(data["operators"]), markup=False)
        return
    console.print(f"ALPHA | {data['dataset']} | {data['expression']}", markup=False)
    for note in data["notes"]: console.print(note, markup=False)
    console.print(f"Data dates: {data.get('first_date')} to {data.get('last_date')}", markup=False)
    if data.get("sources"):
        sources = Table("Security", "Source", "First", "Last", "Fetched (UTC)")
        for row in data["sources"]:
            sources.add_row(row["security"], row["source"], row["first_date"], row["last_date"], row.get("fetched_at") or "Unknown (cached)")
        console.print(sources)
    table = Table("Metric", "Value")
    for key, value in data["metrics"].items(): table.add_row(key, "N/A" if value is None else f"{value:.4f}")
    console.print(table)
    table = Table("Security", "Latest factor")
    for row in data["latest"][:20]: table.add_row(row["security"], str(row["factor"]))
    console.print(table)
