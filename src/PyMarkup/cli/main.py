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
    method: str = typer.Option(
        "wooldridge_iv", "--method", "-m", help="Estimation method (wooldridge_iv, cost_share, acf, all)"
    ),
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
    dataset: str = typer.Argument(..., help="Dataset to download (compustat, cpi, ppi, all)"),
    output: Path = typer.Option("Input/", "--output", "-o", help="Output directory"),
    config: Path = typer.Option(None, "--config", "-c", help="Credentials YAML config file"),
):
    """
    Download data from WRDS, FRED, or BLS.

    Examples:
        $ pymarkup download compustat --output Input/
        $ pymarkup download all --config config.yaml
        $ pymarkup download cpi
        $ pymarkup download ppi
    """
    from PyMarkup.data import download_all, download_compustat, download_cpi, download_ppi, load_config

    cfg = load_config(config)

    downloaders = {
        "compustat": download_compustat,
        "cpi": download_cpi,
        "ppi": download_ppi,
    }

    try:
        if dataset == "all":
            console.print("[blue]Downloading all datasets...[/blue]")
            download_all(config=cfg)
        elif dataset in downloaders:
            console.print(f"[blue]Downloading {dataset}...[/blue]")
            downloaders[dataset](config=cfg, output_dir=output)
        else:
            console.print(f"[red]Unknown dataset: {dataset}. Choose from: compustat, cpi, ppi, all[/red]")
            raise typer.Exit(1)

        console.print("[green]Download complete.[/green]")

    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        raise typer.Exit(1) from e


@app.command("run-all")
def run_all(
    config: Path = typer.Option(None, "--config", "-c", help="YAML config file path"),
    method: str = typer.Option(
        "wooldridge_iv", "--method", "-m", help="Estimation method (wooldridge_iv, cost_share, acf, all)"
    ),
    compustat: Path = typer.Option(None, "--compustat", help="Path to Compustat data"),
    macro_vars: Path = typer.Option(None, "--macro-vars", help="Path to macro variables"),
    output: Path = typer.Option("Output/", "--output", "-o", help="Output directory"),
    skip_download: bool = typer.Option(False, "--skip-download", help="Skip data download step"),
    skip_compustat: bool = typer.Option(False, "--skip-compustat", help="Skip Compustat download (use existing)"),
    skip_cpi: bool = typer.Option(False, "--skip-cpi", help="Skip CPI download (use existing)"),
    skip_ppi: bool = typer.Option(False, "--skip-ppi", help="Skip PPI download (use existing)"),
    no_figures: bool = typer.Option(False, "--no-figures", help="Skip figure generation"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """
    Run the complete pipeline: download -> estimate -> figures.

    This command runs all steps in one go:
    1. Download data from WRDS, FRED, BLS (unless --skip-download)
    2. Prepare and clean Compustat panel data
    3. Estimate production function elasticities
    4. Calculate firm-level markups
    5. Generate output figures (unless --no-figures)

    Examples:
        # Full pipeline with config file
        $ pymarkup run-all --config pipeline_config.yaml

        # Skip download (use existing data)
        $ pymarkup run-all --config config.yaml --skip-download

        # Skip only Compustat download (WRDS credentials not needed)
        $ pymarkup run-all --config config.yaml --skip-compustat

        # Command-line arguments (skip download)
        $ pymarkup run-all --compustat Input/DLEU/Compustat_annual.dta \\
            --macro-vars Input/DLEU/macro_vars_new.xlsx --skip-download
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

    # Run full pipeline
    console.print("\n[bold green]Starting PyMarkup full pipeline...[/bold green]\n")

    try:
        pipeline = MarkupPipeline(cfg)
        results = pipeline.run_all(
            download=not skip_download,
            skip_compustat=skip_compustat,
            skip_cpi=skip_cpi,
            skip_ppi=skip_ppi,
            generate_figures=not no_figures,
        )

        # Save results
        console.print(f"\n[bold green]Saving results to {output}...[/bold green]")
        results.save(output_dir=output, format="csv")

        console.print("\n[bold green]✓ Full pipeline completed successfully![/bold green]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ Pipeline failed: {e}[/bold red]\n")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
