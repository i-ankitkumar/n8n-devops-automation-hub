"""Command-line entry point for n8nhublint."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.table import Table

from n8nhublint import __version__
from n8nhublint.validator import validate_directory

console = Console()
SEVERITY_COLOR = {"error": "bold red", "warning": "yellow"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="n8nhublint",
        description="Validate exported n8n workflow JSON files for structural issues.",
    )
    parser.add_argument("path", nargs="?", default="workflows", help="Directory of *.json workflow exports (default: workflows)")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on warnings too, not just errors.",
    )
    parser.add_argument("--version", action="version", version=f"n8nhublint {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    results = validate_directory(args.path)
    if not results:
        console.print(f"[yellow]No *.json files found under '{args.path}'.[/yellow]")
        return 0

    all_findings = [f for findings in results.values() for f in findings]

    console.print(f"Checked {len(results)} workflow file(s).\n")

    if not all_findings:
        console.print("[bold green]All workflows are structurally valid.[/bold green]")
        return 0

    table = Table(show_lines=True)
    table.add_column("File")
    table.add_column("Rule")
    table.add_column("Severity", no_wrap=True)
    table.add_column("Message")

    for file_name, findings in results.items():
        for f in findings:
            color = SEVERITY_COLOR[f.severity]
            table.add_row(file_name, f.rule_id, f"[{color}]{f.severity.upper()}[/{color}]", f.message)

    console.print(table)

    error_count = sum(1 for f in all_findings if f.severity == "error")
    warning_count = sum(1 for f in all_findings if f.severity == "warning")
    console.print(f"\n[bold red]{error_count} error(s)[/bold red]  [yellow]{warning_count} warning(s)[/yellow]")

    if error_count > 0:
        return 1
    if args.strict and warning_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
