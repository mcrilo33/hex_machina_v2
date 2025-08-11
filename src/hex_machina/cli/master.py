"""Master CLI dispatcher for Hex Machina v2."""

import click

from .datasets.main import manage
from .evaluation.main import evaluation
from .experiments.main import experiments
from .tasks import tasks_cli


@click.group()
@click.version_option(version="0.1.0")
def master_cli():
    """Hex Machina v2 - AI-driven newsletter service

    A comprehensive CLI for managing AI research monitoring and newsletter generation.
    """
    pass


# Add sub-commands for each CLI
master_cli.add_command(tasks_cli, name="tasks")
master_cli.add_command(manage, name="datasets")
master_cli.add_command(evaluation, name="evaluation")
master_cli.add_command(experiments, name="experiments")


# TODO: Add other CLIs when implemented
# master_cli.add_command(workflows_cli, name="workflows")
# master_cli.add_command(prompts_cli, name="prompts")


if __name__ == "__main__":
    master_cli()
