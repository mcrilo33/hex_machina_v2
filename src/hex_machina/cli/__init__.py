"""
Main CLI entry point for hex_machina.
"""

import click

from src.hex_machina.cli.datasets.main import manage
from src.hex_machina.cli.evaluation.main import evaluation
from src.hex_machina.cli.tasks.main import tasks_cli


@click.group()
def cli():
    """Hex Machina CLI - AI-powered content enrichment and evaluation."""
    pass


# Add subcommands
cli.add_command(tasks_cli)
cli.add_command(manage)
cli.add_command(evaluation)


if __name__ == "__main__":
    cli()
