"""Main CLI application for PyMarkup."""

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler

from PyMarkup.pipeline import EstimatorConfig, MarkupPipeline, PipelineConfig

# Setup rich logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_time=False)],
)

app = typer.Typer(
    name="pymarkup",
    help="PyMarkup: Production function-based markup estimation toolkit",
    add_completion=False,
)
console = Console()


@app.command()
def estimate(
    config: Path = typer.Option(None, "--config", "-c", help="YAML config file path"),
    method: str = typer.Option("wooldridge_iv", "--method", "-m", help="Estimation method (wooldridge_iv, cost_share, acf, all)"),
    compustat: Path = typer.Option(None, "--compustat", help="Path to Compustat data"),
    macro_vars: Path = typer.Option(None, "--macro-vars", help="Path to macro variables"),
    output: Path = typer.Option("output/", "--output", "-o", help="Output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """
    Estimate firm-level markups from Compustat data.

    Examples:

        # Using config file
        $ pymarkup estimate --config config.yaml

        # Using command-line arguments
        $ pymarkup estimate --method wooldridge_iv --compustat data.dta --macro-vars macro.xlsx
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load or create config
    if config:
        console.print(f"[blue]Loading configuration from {config}[/blue]")
        cfg = PipelineConfig.from_yaml(config)
        cfg.output_dir = output  # Override output dir
    else:
        if not compustat or not macro_vars:
            console.print("[red]Error: --compustat and --macro-vars required when not using --config[/red]")
            raise typer.Exit(1)

        cfg = PipelineConfig(
            compustat_path=compustat,
            macro_vars_path=macro_vars,
            estimator=EstimatorConfig(method=method),
            output_dir=output,
        )

    # Run pipeline
    console.print("\n[bold green]Starting PyMarkup pipeline...[/bold green]\n")

    try:
        pipeline = MarkupPipeline(cfg)
        results = pipeline.run()

        # Save results
        console.print(f"\n[bold green]Saving results to {output}...[/bold green]")
        results.save(output_dir=output, format="csv")

        console.print("\n[bold green]✓ Pipeline completed successfully![/bold green]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ Pipeline failed: {e}[/bold red]\n")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def validate(
    input_file: Path = typer.Argument(..., help="Input data file to validate"),
):
    """
    Validate input data schema.

    Example:
        $ pymarkup validate data/compustat.dta
    """
    from PyMarkup.io import InputData

    console.print(f"[blue]Validating {input_file}...[/blue]")

    try:
        data = InputData.from_compustat(input_file)
        console.print("[green]✓ Data validation passed[/green]")
        console.print(f"\nData summary:")
        console.print(f"  - Firms: {data.gvkey.nunique()}")
        console.print(f"  - Years: {data.year.min()}-{data.year.max()}")
        console.print(f"  - Observations: {len(data.gvkey)}")
    except Exception as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def version():
    """Show PyMarkup version."""
    from PyMarkup._version import __version__

    console.print(f"PyMarkup version {__version__}")


@app.command()
def download(
    dataset: str = typer.Argument(..., help="Dataset to download (compustat, cpi, ppi)"),
    output: Path = typer.Option("Input/", "--output", "-o", help="Output directory"),
):
    """
    Download data from WRDS, FRED, or BLS.

    Example:
        $ pymarkup download compustat --output Input/
    """
    console.print(f"[yellow]Download functionality not yet implemented for {dataset}[/yellow]")
    # TODO: Implement downloaders


if __name__ == "__main__":
    app()
