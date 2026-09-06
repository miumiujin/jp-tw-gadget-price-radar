from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from .config import load_products
from .fx import fetch_jpy_twd
from .pipeline import run_ingestion
from .sources.iosys import fetch_iosys_used
from .sources.janpara import fetch_janpara_used
from .sources.sofmap import fetch_sofmap_used


app = typer.Typer(help="JP–TW Apple Price Radar", no_args_is_help=True)
console = Console()

SOURCE_MAP = {
    "sofmap": fetch_sofmap_used,
    "janpara": fetch_janpara_used,
    "iosys": fetch_iosys_used,
}


@app.callback()
def main():
    """Compare public Apple used prices in Japan and Taiwan."""


@app.command()
def ingest():
    """Fetch today's FX and all public prices."""
    result = run_ingestion()

    console.print(
        f"[green]Products {result['products']}[/green] | "
        f"observations {result['observations']} | "
        f"JPY/TWD {result['fx_rate']:.5f}"
    )

    for product, source in result["misses"]:
        console.print(f"[yellow]NO MATCH[/yellow] {product} / {source}")

    for product, source, error in result["errors"]:
        console.print(f"[red]ERROR[/red] {product} / {source}: {error}")


@app.command("source-debug")
def source_debug(
    source: str = typer.Argument(..., help="sofmap | janpara | iosys"),
    product_id: str = typer.Argument(..., help="Product id from config/products.yaml"),
):
    """Fetch one product from one Japan retailer."""
    source_key = source.lower()
    if source_key not in SOURCE_MAP:
        console.print("[red]Source must be one of: sofmap, janpara, iosys[/red]")
        raise typer.Exit(code=1)

    products = {p["id"]: p for p in load_products()}
    product = products.get(product_id)
    if product is None:
        console.print(f"[red]Unknown product id:[/red] {product_id}")
        raise typer.Exit(code=1)

    fx_rate, _ = fetch_jpy_twd()
    console.print(f"[cyan]Source:[/cyan] {source_key}")
    console.print(f"[cyan]Product:[/cyan] {product_id}")
    console.print(f"[cyan]JPY/TWD:[/cyan] {fx_rate:.5f}")

    try:
        observations = SOURCE_MAP[source_key](product, fx_rate)
    except Exception as exc:
        console.print(f"[red]Fetch failed:[/red] {type(exc).__name__}: {exc}")
        raise typer.Exit(code=2)

    if not observations:
        console.print("[yellow]Page loaded, but no exact-spec listing matched.[/yellow]")
        raise typer.Exit()

    table = Table(title=f"{source_key} — {product_id}")
    table.add_column("JPY", justify="right")
    table.add_column("TWD", justify="right")
    table.add_column("Title")
    table.add_column("Note")

    for obs in observations:
        table.add_row(
            f"¥{int(obs.price):,}",
            f"NT${int(obs.price_twd):,}",
            obs.raw_title,
            obs.note,
        )

    console.print(table)


if __name__ == "__main__":
    app()
