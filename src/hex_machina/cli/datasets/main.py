"""Dataset management CLI."""

import json

import click

from src.hex_machina.datasets.curation import DatasetCurationManager
from src.hex_machina.datasets.evaluators import get_evaluator, list_evaluators
from src.hex_machina.datasets.manager import DatasetManager


@click.group()
def manage():
    """Manage datasets for evaluation and training."""
    pass


@manage.command()
@click.option("--name-contains", help="Filter datasets by name")
@click.option(
    "--no-auto-sync", is_flag=True, help="Disable automatic sync with LangSmith"
)
def list(name_contains, no_auto_sync):
    """List all datasets."""
    try:
        manager = DatasetManager()

        # Auto-sync if not disabled (default)
        if not no_auto_sync:
            click.echo("🔄 Auto-syncing datasets with LangSmith...")
            try:
                sync_results = manager.sync_all_datasets(
                    force=False, project="hex-machina-v2"
                )
                if (
                    sync_results["created_local"] > 0
                    or sync_results["removed_local"] > 0
                ):
                    click.echo(
                        f"   📥 Synced {sync_results['created_local']} local datasets"
                    )
                    click.echo(
                        f"   🗑️  Removed {sync_results['removed_local']} local datasets"
                    )
            except Exception as e:
                click.echo(f"   ⚠️  Auto-sync warning: {e}")

        datasets = manager.list_datasets(name_contains=name_contains)

        if not datasets:
            click.echo("📭 No datasets found")
            return

        click.echo(f"📊 Found {len(datasets)} dataset(s):")
        click.echo()

        for dataset in datasets:
            click.echo(f"📁 {dataset.name}")
            if dataset.description:
                click.echo(f"   Description: {dataset.description}")
            click.echo(f"   Type: {dataset.data_type}")
            click.echo(f"   Examples: {len(dataset.examples)}")
            if dataset.langsmith_dataset_id:
                click.echo(f"   🔗 LangSmith: {dataset.langsmith_dataset_id}")
            click.echo(f"   Created: {dataset.created_at}")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Error listing datasets: {e}")


@manage.command()
@click.argument("name")
def view(name):
    """View dataset details."""
    try:
        manager = DatasetManager()
        dataset = manager.get_dataset(name)

        if not dataset:
            click.echo(f"❌ Dataset '{name}' not found")
            return

        click.echo(f"📁 Dataset: {dataset.name}")
        click.echo(f"   Description: {dataset.description or 'No description'}")
        click.echo(f"   Type: {dataset.data_type}")
        click.echo(f"   Examples: {len(dataset.examples)}")
        if dataset.langsmith_dataset_id:
            click.echo(f"   🔗 LangSmith: {dataset.langsmith_dataset_id}")
        click.echo(f"   Created: {dataset.created_at}")
        click.echo(f"   Updated: {dataset.updated_at}")

        # Show split distribution
        splits = {}
        for example in dataset.examples:
            if example.split:
                # Handle comma-separated splits
                example_splits = [s.strip() for s in example.split.split(",")]
                for split in example_splits:
                    splits[split] = splits.get(split, 0) + 1
            else:
                splits["no_split"] = splits.get("no_split", 0) + 1

        click.echo("\n📊 Split Distribution:")
        for split, count in splits.items():
            click.echo(f"   {split}: {count} examples")

    except Exception as e:
        click.echo(f"❌ Error viewing dataset: {e}")


@manage.command()
@click.argument("dataset")
@click.argument("article_ids", type=str)
@click.option("--split", default="train", help="Split to add articles to")
def add_articles(dataset, article_ids, split):
    """Add articles to dataset."""
    try:
        # Parse article IDs
        article_id_list = [int(id.strip()) for id in article_ids.split(",")]

        manager = DatasetManager()
        added_count = manager.add_articles_to_dataset(dataset, article_id_list, split)

        click.echo(
            f"✅ Added {added_count} articles to dataset '{dataset}' (split: {split})"
        )

    except ValueError:
        click.echo(
            "❌ Invalid article IDs format. Use comma-separated list (e.g., 1,2,3)"
        )
    except Exception as e:
        click.echo(f"❌ Error adding articles: {e}")


@manage.command()
@click.argument("dataset")
@click.argument("workflow_operation_id")
@click.option("--split", default="train", help="Split to add articles to")
@click.option("--description", help="Dataset description")
def create_from_workflow(dataset, workflow_operation_id, split, description):
    """Create dataset from workflow operation articles."""
    try:
        manager = DatasetManager()
        dataset_obj = manager.create_dataset_from_workflow(
            name=dataset,
            workflow_operation_id=workflow_operation_id,
            split=split,
            description=description,
        )

        click.echo(
            f"✅ Created dataset '{dataset}' from workflow operation '{workflow_operation_id}'"
        )

        # Get fresh dataset data for display
        fresh_dataset = manager.get_dataset(dataset)
        if fresh_dataset:
            click.echo(f"   Examples: {len(fresh_dataset.examples)}")
            if fresh_dataset.langsmith_dataset_id:
                click.echo(
                    f"   🔗 Synced to LangSmith: {fresh_dataset.langsmith_dataset_id}"
                )
        else:
            click.echo("   ⚠️  Could not retrieve dataset details for display")

    except Exception as e:
        click.echo(f"❌ Error creating dataset from workflow: {e}")


@manage.command()
@click.argument("dataset")
@click.argument("ingestion_operation_id", type=int)
@click.option("--split", default="train", help="Split to add articles to")
@click.option("--description", help="Dataset description")
def create_from_ingestion(dataset, ingestion_operation_id, split, description):
    """Create dataset from ingestion operation articles."""
    try:
        manager = DatasetManager()
        dataset_obj = manager.create_dataset_from_ingestion(
            name=dataset,
            ingestion_operation_id=ingestion_operation_id,
            split=split,
            description=description,
        )

        click.echo(
            f"✅ Created dataset '{dataset}' from ingestion operation {ingestion_operation_id}"
        )

        # Get fresh dataset data for display
        fresh_dataset = manager.get_dataset(dataset)
        if fresh_dataset:
            click.echo(f"   Examples: {len(fresh_dataset.examples)}")
            if fresh_dataset.langsmith_dataset_id:
                click.echo(
                    f"   🔗 Synced to LangSmith: {fresh_dataset.langsmith_dataset_id}"
                )
        else:
            click.echo("   ⚠️  Could not retrieve dataset details for display")

    except Exception as e:
        click.echo(f"❌ Error creating dataset from ingestion: {e}")


@manage.command()
@click.argument("dataset")
@click.argument("evaluator_name")
@click.option("--criteria", help="JSON criteria for evaluator")
@click.option("--output-split", help="Output split name")
def apply_evaluator(dataset, evaluator_name, criteria, output_split):
    """Apply boolean evaluator to create custom split."""
    try:
        # Parse criteria
        criteria_dict = {}
        if criteria:
            try:
                criteria_dict = json.loads(criteria)
            except json.JSONDecodeError:
                click.echo("❌ Invalid JSON criteria")
                return

        # Get evaluator
        evaluator = get_evaluator(evaluator_name)

        # Apply evaluator
        manager = DatasetManager()
        moved_count = manager.apply_evaluator_for_split(
            dataset_name=dataset,
            evaluator=evaluator,
            criteria=criteria_dict,
            output_split=output_split or f"custom_{evaluator_name}",
        )

        click.echo(
            f"✅ Moved {moved_count} examples to split '{output_split or f'custom_{evaluator_name}'}'"
        )

    except Exception as e:
        click.echo(f"❌ Error applying evaluator: {e}")


@manage.command()
def list_evaluators():
    """List available boolean evaluators."""
    try:
        evaluators = list_evaluators()

        click.echo("🔍 Available Boolean Evaluators:")
        click.echo()

        for evaluator in evaluators:
            click.echo(f"📋 {evaluator['name']}")
            click.echo(f"   {evaluator['description']}")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Error listing evaluators: {e}")


@manage.command()
@click.argument("dataset")
@click.option(
    "--max-items", type=int, default=3, help="Maximum number of items in small split"
)
@click.option("--split-name", default="small", help="Name for the small split")
def create_small_split(dataset, max_items, split_name):
    """Create a small split with first few articles for quick testing."""
    try:
        manager = DatasetManager()
        added_count = manager.create_small_split(
            dataset_name=dataset,
            max_items=max_items,
            split_name=split_name,
        )

        click.echo(
            f"✅ Created '{split_name}' split for dataset '{dataset}' with {added_count} articles"
        )

    except Exception as e:
        click.echo(f"❌ Error creating small split: {e}")


@manage.command()
@click.argument("dataset")
@click.option("--split", help="Filter by split")
def list_articles(dataset, split):
    """List articles in dataset."""
    try:
        manager = DatasetManager()
        articles = manager.list_articles_in_dataset(dataset, split=split)

        if not articles:
            click.echo(f"📭 No articles found in dataset '{dataset}'")
            return

        click.echo(f"📄 Articles in dataset '{dataset}':")
        if split:
            click.echo(f"   Split: {split}")
        click.echo()

        for article in articles:
            click.echo(f"📝 {article['article_id']}: {article['title'][:60]}...")
            click.echo(f"   URL: {article['url']}")
            if article["split"]:
                splits = [s.strip() for s in article["split"].split(",")]
                click.echo(f"   Splits: {', '.join(splits)}")
            else:
                click.echo("   Split: none")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Error listing articles: {e}")


@manage.command()
@click.option("--force", is_flag=True, help="Force sync even if datasets exist locally")
@click.option("--project", default="hex-machina-v2", help="LangSmith project name")
def sync_all(force, project):
    """Sync all datasets between LangSmith and local database."""
    try:
        manager = DatasetManager()
        click.echo("🔄 Syncing all datasets between LangSmith and local database...")

        # Get sync results
        sync_results = manager.sync_all_datasets(force=force, project=project)

        click.echo("\n✅ Sync completed!")
        click.echo(f"   �� Created locally: {sync_results['created_local']}")
        click.echo(f"   🗑️  Removed locally: {sync_results['removed_local']}")
        click.echo(f"   ❌ Errors: {sync_results['errors']}")

        if sync_results["errors"]:
            click.echo("\n⚠️  Some errors occurred during sync. Check logs for details.")

    except Exception as e:
        click.echo(f"❌ Error during sync: {e}")


@manage.command()
@click.argument("dataset")
@click.option("--project", default="hex-machina-v2", help="LangSmith project name")
def sync_langsmith(dataset, project):
    """Sync dataset to LangSmith."""
    try:
        manager = DatasetManager()
        dataset_obj = manager.get_dataset(dataset)

        if not dataset_obj:
            click.echo(f"❌ Dataset '{dataset}' not found")
            return

        if dataset_obj.langsmith_dataset_id:
            click.echo(
                f"✅ Dataset already synced to LangSmith: {dataset_obj.langsmith_dataset_id}"
            )
        else:
            click.echo("🔄 Syncing to LangSmith...")
            # This would trigger a sync operation
            click.echo("⚠️  Manual sync not implemented yet")

    except Exception as e:
        click.echo(f"❌ Error syncing to LangSmith: {e}")


@manage.command()
@click.argument("dataset")
@click.option("--split", help="Specific split to curate")
@click.option("--display-fields", help="Comma-separated fields to display")
@click.option("--annotate-fields", help="Comma-separated fields to annotate")
def curate(dataset, split, display_fields, annotate_fields):
    """Interactively curate a dataset - creates LangSmith splits."""
    try:
        # Parse field lists
        display_field_list = None
        if display_fields:
            display_field_list = [f.strip() for f in display_fields.split(",")]

        annotate_field_list = None
        if annotate_fields:
            annotate_field_list = [f.strip() for f in annotate_fields.split(",")]

        # Run curation
        curator = DatasetCurationManager()
        curator.curate_dataset(
            dataset_name=dataset,
            split=split,
            display_fields=display_field_list,
            annotate_fields=annotate_field_list,
        )

    except Exception as e:
        click.echo(f"❌ Error during curation: {e}")


if __name__ == "__main__":
    manage()
