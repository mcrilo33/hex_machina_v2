"""Dataset management CLI."""

import click
import json
from typing import List
from src.hex_machina.datasets.manager import DatasetManager
from src.hex_machina.datasets.evaluators import get_evaluator, list_evaluators


@click.group()
def manage():
    """Manage datasets for evaluation and training."""
    pass


@manage.command()
@click.argument("name")
@click.option("--description", help="Dataset description")
@click.option("--data-type", default="kv", help="Data type (kv, chat)")
@click.option("--metadata", help="JSON metadata")
def create(name, description, data_type, metadata):
    """Create a new dataset."""
    try:
        manager = DatasetManager()
        
        # Parse metadata if provided
        metadata_dict = None
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                click.echo("❌ Invalid JSON metadata")
                return

        dataset = manager.create_dataset(
            name=name,
            description=description,
            data_type=data_type,
            metadata=metadata_dict,
        )
        
        click.echo(f"✅ Created dataset '{name}' (ID: {dataset.id})")
        if dataset.langsmith_dataset_id:
            click.echo(f"🔗 Synced to LangSmith: {dataset.langsmith_dataset_id}")
            
    except Exception as e:
        click.echo(f"❌ Error creating dataset: {e}")


@manage.command()
@click.option("--name-contains", help="Filter datasets by name")
def list(name_contains):
    """List all datasets."""
    try:
        manager = DatasetManager()
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
            split = example.split
            splits[split] = splits.get(split, 0) + 1
            
        click.echo("\n📊 Split Distribution:")
        for split, count in splits.items():
            click.echo(f"   {split}: {count} examples")
            
    except Exception as e:
        click.echo(f"❌ Error viewing dataset: {e}")


@manage.command()
@click.argument("name")
def delete(name):
    """Delete a dataset."""
    try:
        manager = DatasetManager()
        if manager.delete_dataset(name):
            click.echo(f"✅ Deleted dataset '{name}'")
        else:
            click.echo(f"❌ Dataset '{name}' not found")
    except Exception as e:
        click.echo(f"❌ Error deleting dataset: {e}")


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
        
        click.echo(f"✅ Added {added_count} articles to dataset '{dataset}' (split: {split})")
        
    except ValueError:
        click.echo("❌ Invalid article IDs format. Use comma-separated list (e.g., 1,2,3)")
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
        
        click.echo(f"✅ Created dataset '{dataset}' from workflow operation '{workflow_operation_id}'")
        click.echo(f"   Examples: {len(dataset_obj.examples)}")
        if dataset_obj.langsmith_dataset_id:
            click.echo(f"   🔗 Synced to LangSmith: {dataset_obj.langsmith_dataset_id}")
            
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
        
        click.echo(f"✅ Created dataset '{dataset}' from ingestion operation {ingestion_operation_id}")
        click.echo(f"   Examples: {len(dataset_obj.examples)}")
        if dataset_obj.langsmith_dataset_id:
            click.echo(f"   🔗 Synced to LangSmith: {dataset_obj.langsmith_dataset_id}")
            
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
        
        click.echo(f"✅ Moved {moved_count} examples to split '{output_split or f'custom_{evaluator_name}'}'")
        
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
            click.echo(f"   Split: {article['split']}")
            click.echo()
            
    except Exception as e:
        click.echo(f"❌ Error listing articles: {e}")


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
            click.echo(f"✅ Dataset already synced to LangSmith: {dataset_obj.langsmith_dataset_id}")
        else:
            click.echo("🔄 Syncing to LangSmith...")
            # This would trigger a sync operation
            click.echo("⚠️  Manual sync not implemented yet")
            
    except Exception as e:
        click.echo(f"❌ Error syncing to LangSmith: {e}")


if __name__ == "__main__":
    manage() 