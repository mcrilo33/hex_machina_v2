"""CLI for task management."""

import asyncio
import json

import click
from dotenv import load_dotenv

from src.hex_machina.enrichment.core.article_source import ArticleSource
from src.hex_machina.enrichment.tasks.runner import task_runner

# Load environment variables
load_dotenv()


def validate_source_options(
    article_id,
    article_ids,
    ingestion_operation_id,
    dataset_name,
    all_articles,
    input_file,
):
    """Ensure only one source is specified."""
    sources = []
    if article_id is not None:
        sources.append("article_id")
    if article_ids is not None:
        sources.append("article_ids")
    if ingestion_operation_id is not None:
        sources.append("ingestion_operation_id")
    if dataset_name is not None:
        sources.append("dataset_name")
    if all_articles:
        sources.append("all_articles")
    if input_file is not None:
        sources.append("input_file")

    if len(sources) == 0:
        raise click.UsageError("Must specify one article source")
    elif len(sources) > 1:
        raise click.UsageError(
            f"Can only specify one article source. Found: {', '.join(sources)}"
        )


@click.group()
def tasks_cli():
    """Task management commands."""
    pass


@tasks_cli.command()
@click.option("-t", "--task", required=True, help="Task name to run")
@click.option("--article-id", type=int, help="Single article ID")
@click.option("--article-ids", help="Comma-separated article IDs")
@click.option("--ingestion-operation-id", type=int, help="Ingestion operation ID")
@click.option("--dataset-name", help="Dataset name")
@click.option("--all-articles", is_flag=True, help="Process all articles")
@click.option("-i", "--input-file", help="Input JSON file (legacy)")
@click.option("--confirm", is_flag=True, help="Confirm destructive operations")
@click.option("--batch-size", type=int, default=10, help="Batch size for processing")
@click.option("--max-concurrent", type=int, default=3, help="Max concurrent tasks")
@click.option("--dry-run", is_flag=True, help="Show what would be processed")
@click.option("--limit", type=int, help="Limit number of articles to process")
@click.option("--skip-existing", is_flag=True, help="Skip already processed articles")
@click.option("--output-dir", help="Output directory for results")
@click.option(
    "--format", type=click.Choice(["json", "csv"]), default="json", help="Output format"
)
@click.option("--save-to-db", is_flag=True, help="Force save to database")
@click.option("--no-save-to-db", is_flag=True, help="Disable database saving")
def run(
    task,
    article_id,
    article_ids,
    ingestion_operation_id,
    dataset_name,
    all_articles,
    input_file,
    confirm,
    batch_size,
    max_concurrent,
    dry_run,
    limit,
    skip_existing,
    output_dir,
    format,
    save_to_db,
    no_save_to_db,
):
    """Run enrichment tasks on articles from various sources."""

    # Validate source options
    validate_source_options(
        article_id,
        article_ids,
        ingestion_operation_id,
        dataset_name,
        all_articles,
        input_file,
    )

    # Handle confirmation for destructive operations
    if all_articles and not confirm:
        click.echo("⚠️  Running on ALL articles in database. Use --confirm to proceed.")
        return

    # Parse article IDs if provided
    parsed_article_ids = None
    if article_ids:
        try:
            parsed_article_ids = [int(id.strip()) for id in article_ids.split(",")]
        except ValueError:
            raise click.UsageError(
                "Invalid article IDs format. Use comma-separated integers."
            )

    # Determine source type and value
    source_type = None
    source_value = None

    if article_id is not None:
        source_type = "single_article"
        source_value = article_id
    elif parsed_article_ids is not None:
        source_type = "multiple_articles"
        source_value = parsed_article_ids
    elif ingestion_operation_id is not None:
        source_type = "ingestion_operation"
        source_value = ingestion_operation_id
    elif dataset_name is not None:
        source_type = "dataset"
        source_value = dataset_name
    elif all_articles:
        source_type = "all_articles"
        source_value = limit
    elif input_file is not None:
        # Handle legacy input file case
        asyncio.run(_run_task_on_input_file(task, input_file))
        return

    # Validate source
    article_source = ArticleSource()
    if not article_source.validate_source(source_type, source_value):
        click.echo(f"❌ No articles found for source: {source_type}={source_value}")
        return

    # Get article count for dry run
    article_count = article_source.get_article_count(source_type, source_value)
    if dry_run:
        click.echo(f"🔍 DRY RUN: Would process {article_count} articles")
        click.echo(f"   Task: {task}")
        click.echo(f"   Source: {source_type}={source_value}")
        click.echo(f"   Batch size: {batch_size}")
        click.echo(f"   Max concurrent: {max_concurrent}")
        if limit:
            click.echo(f"   Limit: {limit}")
        if skip_existing:
            click.echo("   Skip existing: Yes")
        return

    # Run the task
    click.echo(f"🚀 Running task '{task}' on {article_count} articles...")

    try:
        results = asyncio.run(
            task_runner.run_task_on_source(
                task_name=task,
                source_type=source_type,
                source_value=source_value,
                batch_size=batch_size,
                max_concurrent=max_concurrent,
                skip_existing=skip_existing,
                limit=limit,
            )
        )

        # Display results
        click.echo(f"✅ Completed! Processed {len(results)} articles")

        # Save results to file if output directory specified
        if output_dir:
            _save_results_to_file(results, output_dir, format)

        # Show summary
        _show_results_summary(results)

    except Exception as e:
        click.echo(f"❌ Error running task: {e}")
        if click.get_current_context().obj.get("debug", False):
            import traceback

            traceback.print_exc()


async def _run_task_on_input_file(task_name: str, input_file: str):
    """Run task on input file (legacy method)."""
    try:
        # Load input data
        with open(input_file, "r") as f:
            input_data = json.load(f)

        click.echo(f"🚀 Running task '{task_name}' on input file...")

        # Run task
        result = await task_runner.run_task(task_name, input_data)

        # Display result
        click.echo("✅ Task completed!")
        click.echo(json.dumps(result.model_dump(), indent=2, default=str))

    except Exception as e:
        click.echo(f"❌ Error running task: {e}")


def _save_results_to_file(results, output_dir, format):
    """Save results to file in specified format."""
    import os
    from datetime import datetime

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "json":
        filename = os.path.join(output_dir, f"task_results_{timestamp}.json")
        with open(filename, "w") as f:
            json.dump([r.model_dump() for r in results], f, indent=2, default=str)
    elif format == "csv":
        import csv

        filename = os.path.join(output_dir, f"task_results_{timestamp}.csv")
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["task_id", "task_name", "execution_time", "error"]
            )
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        "task_id": result.task_id,
                        "task_name": result.task_name,
                        "execution_time": result.execution_time,
                        "error": result.error,
                    }
                )

    click.echo(f"📁 Results saved to: {filename}")


def _show_results_summary(results):
    """Show a summary of task results."""
    if not results:
        return

    successful = [r for r in results if r.error is None]
    failed = [r for r in results if r.error is not None]

    click.echo("\n📊 Summary:")
    click.echo(f"   ✅ Successful: {len(successful)}")
    click.echo(f"   ❌ Failed: {len(failed)}")

    if successful:
        avg_time = sum(r.execution_time for r in successful) / len(successful)
        click.echo(f"   ⏱️  Average execution time: {avg_time:.2f}s")

    if failed:
        click.echo("\n❌ Failed tasks:")
        for result in failed[:5]:  # Show first 5 failures
            click.echo(f"   - {result.task_id}: {result.error}")
        if len(failed) > 5:
            click.echo(f"   ... and {len(failed) - 5} more")


@tasks_cli.command()
@click.option("--task", help="Filter by task name")
@click.option("--limit", type=int, default=10, help="Number of runs to show")
def list_runs(task, limit):
    """List recent task runs."""
    try:
        # This would need to be implemented in task storage
        click.echo("📋 Recent task runs:")
        click.echo("(Implementation needed)")

    except Exception as e:
        click.echo(f"❌ Error listing runs: {e}")


@tasks_cli.command()
def list_tasks():
    """List available tasks."""
    try:
        tasks = task_runner._task_registry.list_tasks()
        click.echo("📋 Available Tasks:")
        for task in tasks:
            click.echo(f"  • {task}")

    except Exception as e:
        click.echo(f"❌ Error listing tasks: {e}")


@tasks_cli.command()
@click.argument("task_id")
def show_run(task_id):
    """Show details of a specific task run."""
    try:
        # This would need to be implemented in task storage
        click.echo(f"📋 Task run: {task_id}")
        click.echo("(Implementation needed)")

    except Exception as e:
        click.echo(f"❌ Error showing run: {e}")


@tasks_cli.command()
@click.option("--task", help="Filter by task name")
def stats(task):
    """Show task execution statistics."""
    try:
        # This would need to be implemented in task storage
        click.echo("📊 Task Statistics:")
        click.echo("(Implementation needed)")

    except Exception as e:
        click.echo(f"❌ Error showing stats: {e}")
