"""Dataset manager for handling dataset operations with LangSmith sync."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import joinedload

from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import (
    ArticleDB,
    DatasetDB,
    DatasetExampleDB,
    EnrichmentDB,
    IngestionOperationDB,
)

from .evaluators import BooleanEvaluator
from .langsmith_sync import LangSmithSync

logger = logging.getLogger(__name__)


class DatasetManager:
    """Manages datasets with automatic LangSmith synchronization."""

    def __init__(self):
        """Initialize the dataset manager."""
        from src.hex_machina.enrichment.config.database_config import (
            database_config_manager,
        )

        # Get the correct database path from configuration
        db_path = database_config_manager.get_db_path()
        self.storage = get_storage_manager(db_path)
        self.langsmith_sync = LangSmithSync()

    def create_dataset(
        self,
        name: str,
        description: Optional[str] = None,
        data_type: str = "kv",
        metadata: Optional[Dict[str, Any]] = None,
        auto_create_small_split: bool = True,
    ) -> DatasetDB:
        """Create dataset with automatic LangSmith sync."""
        # First, sync to ensure any stale local datasets are cleaned up
        cleanup_successful = True
        try:
            # Get fresh dataset list for sync
            local_datasets = self._get_local_datasets()
            langsmith_datasets = self.langsmith_sync.list_datasets()

            # Remove local datasets that don't exist in LangSmith
            removed_count = 0
            for local_dataset in local_datasets:
                if local_dataset.name not in {ds["name"] for ds in langsmith_datasets}:
                    try:
                        # Use a separate session for each deletion to avoid transaction conflicts
                        with self.storage.session() as delete_session:
                            # Delete examples first
                            examples_deleted = delete_session.execute(
                                text(
                                    "DELETE FROM dataset_examples WHERE dataset_id = :dataset_id"
                                ),
                                {"dataset_id": local_dataset.id},
                            ).rowcount

                            # Commit examples deletion
                            delete_session.commit()

                            # Now delete the dataset
                            dataset_deleted = delete_session.execute(
                                text("DELETE FROM datasets WHERE id = :dataset_id"),
                                {"dataset_id": local_dataset.id},
                            ).rowcount

                            # Commit dataset deletion
                            delete_session.commit()

                            if dataset_deleted > 0:
                                removed_count += 1
                                logger.info(
                                    f"Removed dataset '{local_dataset.name}' with {examples_deleted} examples"
                                )
                            else:
                                logger.warning(
                                    f"Failed to remove dataset '{local_dataset.name}' - dataset not found"
                                )

                    except Exception as e:
                        logger.error(
                            f"Failed to remove stale dataset '{local_dataset.name}': {e}"
                        )
                        # Mark cleanup as failed
                        cleanup_successful = False

            if removed_count > 0:
                logger.info(
                    f"Cleaned up {removed_count} stale datasets before creating '{name}'"
                )
            else:
                logger.info("No stale datasets found, proceeding with creation")

        except Exception as e:
            logger.error(f"Pre-creation cleanup failed: {e}")
            cleanup_successful = False

        # If cleanup failed, we can't proceed safely
        if not cleanup_successful:
            raise RuntimeError(
                f"Failed to clean up stale datasets before creating '{name}'. "
                "Please run 'datasets sync-all' manually to resolve conflicts."
            )

        with self.storage.session() as session:
            # Check if dataset already exists locally
            existing = session.query(DatasetDB).filter(DatasetDB.name == name).first()

            if existing:
                # Dataset already exists locally, can't create duplicate
                raise ValueError(f"Dataset '{name}' already exists")

            # Create dataset with a safe ID that avoids conflicts
            # DuckDB doesn't support auto-increment like other databases, so we need to manage IDs manually
            try:
                # Get the highest existing ID and add a safe offset
                result = session.execute(
                    text("SELECT COALESCE(MAX(id), 0) FROM datasets")
                ).fetchone()
                max_id = result[0] if result else 0
                next_id = max_id + 10  # Use offset to avoid conflicts

                # Double-check that this ID doesn't exist
                existing_id = session.execute(
                    text("SELECT id FROM datasets WHERE id = :id"), {"id": next_id}
                ).fetchone()

                if existing_id:
                    # If ID exists, find the next available one
                    next_id = max_id + 1
                    while True:
                        existing_id = session.execute(
                            text("SELECT id FROM datasets WHERE id = :id"),
                            {"id": next_id},
                        ).fetchone()
                        if not existing_id:
                            break
                        next_id += 1

                dataset = DatasetDB(
                    id=next_id,
                    name=name,
                    description=description,
                    data_type=data_type,
                    dataset_metadata=metadata or {},
                )
            except Exception as e:
                logger.warning(f"ID generation failed, using fallback: {e}")
                # Fallback: use a timestamp-based ID
                import time

                fallback_id = (
                    int(time.time() * 1000) % 1000000
                )  # Use milliseconds as ID
                dataset = DatasetDB(
                    id=fallback_id,
                    name=name,
                    description=description,
                    data_type=data_type,
                    dataset_metadata=metadata or {},
                )
            session.add(dataset)
            session.flush()  # Get the ID

            # Sync to LangSmith
            try:
                langsmith_dataset = self.langsmith_sync.create_dataset(
                    name=name,
                    description=description,
                    data_type=data_type,
                )
                dataset.langsmith_dataset_id = langsmith_dataset.id
                session.commit()
                logger.info(f"Created dataset '{name}' with LangSmith sync")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to sync dataset '{name}' to LangSmith: {e}")
                # Don't raise here, just log the error
                session.commit()  # Commit the dataset even if LangSmith sync fails

            return dataset

    def _create_small_split_from_articles(
        self,
        dataset_name: str,
        articles: List[ArticleDB],
        max_items: int = 3,
    ) -> int:
        """Create a small split with the first few articles for quick testing.

        This method:
        1. Creates examples with NO split (they go to default split)
        2. Uses LangSmith update_dataset_splits to add first 3 examples to "small" split
        3. Result: First 3 examples are in both default split AND small split
        """
        if not articles:
            return 0

        # Take only the first max_items articles for the small split
        small_articles = articles[:max_items]
        small_article_ids = [article.id for article in small_articles]

        try:
            with self.storage.session() as session:
                dataset = (
                    session.query(DatasetDB)
                    .filter(DatasetDB.name == dataset_name)
                    .first()
                )

                if not dataset:
                    logger.warning(
                        f"Dataset '{dataset_name}' not found for small split creation"
                    )
                    return 0

                # Get the examples for the first few articles (they should already exist with no split)
                small_examples = (
                    session.query(DatasetExampleDB)
                    .filter(
                        DatasetExampleDB.dataset_id == dataset.id,
                        DatasetExampleDB.article_id.in_(small_article_ids),
                    )
                    .all()
                )

                if not small_examples:
                    logger.warning(
                        f"No examples found for small split creation in dataset '{dataset_name}'"
                    )
                    return 0

                # Now use LangSmith update_dataset_splits to add these examples to the "small" split
                if dataset.langsmith_dataset_id:
                    try:
                        # Get the LangSmith example IDs for the small split examples
                        small_example_ids = [
                            example.langsmith_example_id
                            for example in small_examples
                            if example.langsmith_example_id
                        ]

                        if small_example_ids:
                            # Use the proper LangSmith method to add examples to the "small" split
                            self.langsmith_sync.update_dataset_splits(
                                dataset_id=dataset.langsmith_dataset_id,
                                split_name="small",
                                example_ids=small_example_ids,
                                remove=False,  # Add to the split
                            )

                            logger.info(
                                f"Added {len(small_example_ids)} examples to 'small' split in LangSmith"
                            )
                            return len(small_example_ids)
                        else:
                            logger.warning(
                                "No LangSmith example IDs found for small split creation"
                            )
                            return 0

                    except Exception as e:
                        logger.warning(
                            f"Failed to create small split in LangSmith: {e}"
                        )
                        return 0
                else:
                    logger.warning(
                        "Dataset has no LangSmith ID, cannot create small split"
                    )
                    return 0

        except Exception as e:
            logger.warning(
                f"Failed to create small split for dataset '{dataset_name}': {e}"
            )
            return 0

    def add_articles_to_dataset(
        self,
        dataset_name: str,
        article_ids: List[int],
        split: Optional[
            str
        ] = None,  # Changed to Optional, None means no split (default)
        inputs_template: Optional[Dict[str, Any]] = None,
        outputs_template: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Add articles to dataset with automatic LangSmith sync.

        Args:
            dataset_name: Name of the dataset
            article_ids: List of article IDs to add
            split: Split name (None = no split, goes to default split)
            inputs_template: Template for inputs
            outputs_template: Template for outputs
        """
        with self.storage.session() as session:
            dataset = (
                session.query(DatasetDB).filter(DatasetDB.name == dataset_name).first()
            )
            if not dataset:
                raise ValueError(f"Dataset '{dataset_name}' not found")

            # Get articles
            articles = (
                session.query(ArticleDB).filter(ArticleDB.id.in_(article_ids)).all()
            )
            if len(articles) != len(article_ids):
                found_ids = {article.id for article in articles}
                missing_ids = set(article_ids) - found_ids
                raise ValueError(f"Articles not found: {missing_ids}")

            added_count = 0
            examples_to_sync = []

            for article in articles:
                # Check if example already exists
                existing = (
                    session.query(DatasetExampleDB)
                    .filter(
                        DatasetExampleDB.dataset_id == dataset.id,
                        DatasetExampleDB.article_id == article.id,
                        DatasetExampleDB.split
                        == split,  # This will match None if split is None
                    )
                    .first()
                )

                if existing:
                    logger.warning(
                        f"Article {article.id} already in dataset '{dataset_name}' split '{split or 'default'}'"
                    )
                    continue

                # Create inputs/outputs
                inputs = inputs_template or {
                    "article_id": article.id,
                    "title": article.title,
                    "text_content": article.text_content,
                    "url": article.url,
                }
                outputs = outputs_template or {}

                # Get next ID for example
                result = session.execute(
                    text("SELECT COALESCE(MAX(id), 0) + 1 FROM dataset_examples")
                ).fetchone()
                next_example_id = result[0] if result else 1

                # Create example (split can be None for default split)
                example = DatasetExampleDB(
                    id=next_example_id,
                    dataset_id=dataset.id,
                    article_id=article.id,
                    inputs=inputs,
                    outputs=outputs,
                    split=split,  # This can be None for default split
                    example_metadata={
                        "article_title": article.title,
                        "article_url": article.url,
                        "article_domain": article.url_domain,
                    },
                )
                session.add(example)
                examples_to_sync.append(example)
                added_count += 1

            session.flush()  # Get IDs

            # Sync to LangSmith
            if dataset.langsmith_dataset_id and examples_to_sync:
                try:
                    langsmith_example_ids = self.langsmith_sync.add_examples_to_dataset(
                        dataset_id=dataset.langsmith_dataset_id,
                        examples=examples_to_sync,
                    )
                    # Update LangSmith example IDs with actual IDs
                    for i, example in enumerate(examples_to_sync):
                        if i < len(langsmith_example_ids):
                            example.langsmith_example_id = langsmith_example_ids[i]
                    session.commit()
                    logger.info(
                        f"Added {added_count} articles to dataset '{dataset_name}' with LangSmith sync"
                    )
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to sync examples to LangSmith: {e}")
                    raise

            return added_count

    def create_dataset_from_workflow(
        self,
        name: str,
        workflow_operation_id: str,
        split: str = "train",
        description: Optional[str] = None,
    ) -> DatasetDB:
        """Create dataset from articles in a workflow operation."""
        with self.storage.session() as session:
            # Get articles from workflow operation
            articles = (
                session.query(ArticleDB)
                .join(EnrichmentDB)
                .filter(EnrichmentDB.workflow_operation_id == workflow_operation_id)
                .distinct()
                .all()
            )

            if not articles:
                raise ValueError(
                    f"No articles found for workflow operation '{workflow_operation_id}'"
                )

            # Create dataset
            dataset = self.create_dataset(
                name=name,
                description=description
                or f"Dataset from workflow operation {workflow_operation_id}",
            )

            # Add ALL articles to the base split first
            article_ids = [article.id for article in articles]
            self.add_articles_to_dataset(
                name, article_ids, split=None
            )  # None = default split

            # Now create the small split (which will add the first 3 articles to small split as well)
            self._create_small_split_from_articles(name, articles, max_items=3)

            # Ensure all changes are committed before querying
            session.commit()

            # Get the fresh dataset object bound to the current session
            fresh_dataset = (
                session.query(DatasetDB).filter(DatasetDB.name == name).first()
            )
            return fresh_dataset

    def create_dataset_from_ingestion(
        self,
        name: str,
        ingestion_operation_id: int,
        split: str = "train",
        description: Optional[str] = None,
    ) -> DatasetDB:
        """Create dataset from articles in an ingestion operation."""
        with self.storage.session() as session:
            # Get articles from ingestion operation
            articles = (
                session.query(ArticleDB)
                .join(IngestionOperationDB)
                .filter(IngestionOperationDB.id == ingestion_operation_id)
                .distinct()
                .all()
            )

            if not articles:
                raise ValueError(
                    f"No articles found for ingestion operation {ingestion_operation_id}"
                )

            # Create dataset
            dataset = self.create_dataset(
                name=name,
                description=description
                or f"Dataset from ingestion operation {ingestion_operation_id}",
            )

            # Add ALL articles to the base split first
            article_ids = [article.id for article in articles]
            self.add_articles_to_dataset(
                name, article_ids, split=None
            )  # None = default split

            # Now create the small split (which will add the first 3 articles to small split as well)
            self._create_small_split_from_articles(name, articles, max_items=3)

            # Ensure all changes are committed before querying
            session.commit()

            # Get the fresh dataset object bound to the current session
            fresh_dataset = (
                session.query(DatasetDB).filter(DatasetDB.name == name).first()
            )
            return fresh_dataset

    def apply_evaluator_for_split(
        self,
        dataset_name: str,
        evaluator: BooleanEvaluator,
        criteria: Dict[str, Any],
        output_split: str,
    ) -> int:
        """Apply boolean evaluator to create custom split."""
        with self.storage.session() as session:
            dataset = (
                session.query(DatasetDB).filter(DatasetDB.name == dataset_name).first()
            )
            if not dataset:
                raise ValueError(f"Dataset '{dataset_name}' not found")

            # Get all examples
            examples = (
                session.query(DatasetExampleDB)
                .filter(DatasetExampleDB.dataset_id == dataset.id)
                .all()
            )

            moved_count = 0
            examples_to_sync = []

            for example in examples:
                article = (
                    session.query(ArticleDB)
                    .filter(ArticleDB.id == example.article_id)
                    .first()
                )
                if not article:
                    continue

                # Apply evaluator
                if evaluator.evaluate(article, criteria):
                    # Move to new split
                    example.split = output_split
                    examples_to_sync.append(example)
                    moved_count += 1

            session.flush()

            # Sync to LangSmith
            if dataset.langsmith_dataset_id and examples_to_sync:
                try:
                    self.langsmith_sync.update_examples_split(
                        dataset_id=dataset.langsmith_dataset_id,
                        examples=examples_to_sync,
                        new_split=output_split,
                    )
                    session.commit()
                    logger.info(
                        f"Moved {moved_count} examples to split '{output_split}' with LangSmith sync"
                    )
                except Exception as e:
                    logger.error(f"Failed to sync split changes to LangSmith: {e}")
                    # Don't rollback, just commit the local changes
                    session.commit()
                    logger.info(
                        f"Moved {moved_count} examples to split '{output_split}' (local only)"
                    )

            return moved_count

    def sync_all_datasets(
        self, force: bool = False, project: str = "hex-machina-v2"
    ) -> Dict[str, int]:
        """Sync all datasets between LangSmith and local database.

        LangSmith is the source of truth. This method:
        - Creates local datasets for LangSmith datasets that don't exist locally
        - Removes local datasets that don't exist in LangSmith

        Args:
            force: Force sync even if datasets exist locally
            project: LangSmith project name

        Returns:
            Dictionary with sync results
        """
        sync_results = {
            "created_local": 0,
            "removed_local": 0,
            "errors": 0,
        }

        try:
            # Get LangSmith datasets (source of truth)
            langsmith_datasets = self.langsmith_sync.list_datasets()
            langsmith_dataset_names = {ds["name"] for ds in langsmith_datasets}

            # Get local datasets
            local_datasets = self._get_local_datasets()
            local_dataset_names = {ds.name for ds in local_datasets}

            # Create local datasets for LangSmith datasets that don't exist locally
            for ls_dataset in langsmith_datasets:
                if ls_dataset["name"] not in local_dataset_names or force:
                    try:
                        # Create new local dataset
                        with self.storage.session() as session:
                            # Get next ID for dataset
                            result = session.execute(
                                text("SELECT COALESCE(MAX(id), 0) + 1 FROM datasets")
                            ).fetchone()
                            next_id = result[0] if result else 1

                            # Create dataset directly
                            from src.hex_machina.storage.models import DatasetDB

                            local_dataset = DatasetDB(
                                id=next_id,
                                name=ls_dataset["name"],
                                description=ls_dataset["description"],
                                data_type=ls_dataset["data_type"] or "kv",
                                dataset_metadata={},
                                langsmith_dataset_id=ls_dataset["id"],
                            )
                            session.add(local_dataset)
                            session.commit()

                        sync_results["created_local"] += 1
                        logger.info(
                            f"Created local dataset '{ls_dataset['name']}' from LangSmith"
                        )

                    except Exception as e:
                        logger.error(
                            f"Failed to create local dataset '{ls_dataset['name']}': {e}"
                        )
                        sync_results["errors"] += 1

            # Remove local datasets that don't exist in LangSmith
            for local_dataset in local_datasets:
                if local_dataset.name not in langsmith_dataset_names:
                    try:
                        # Delete all examples first (due to foreign key constraint)
                        with self.storage.session() as session:
                            examples = (
                                session.query(DatasetExampleDB)
                                .filter(DatasetExampleDB.dataset_id == local_dataset.id)
                                .all()
                            )

                            for example in examples:
                                session.delete(example)

                            # Commit the example deletions first
                            session.commit()
                            logger.info(
                                f"Deleted {len(examples)} examples from dataset '{local_dataset.name}'"
                            )

                            # Now delete the dataset
                            session.delete(local_dataset)
                            session.commit()

                        sync_results["removed_local"] += 1
                        logger.info(
                            f"Removed local dataset '{local_dataset.name}' (not in LangSmith)"
                        )

                    except Exception as e:
                        logger.error(
                            f"Failed to remove local dataset '{local_dataset.name}': {e}"
                        )
                        sync_results["errors"] += 1

            logger.info(f"Dataset sync completed: {sync_results}")

        except Exception as e:
            logger.error(f"Failed to sync datasets: {e}")
            sync_results["errors"] += 1

        return sync_results

    def _get_local_datasets(self) -> List[DatasetDB]:
        """Get local datasets without triggering sync (internal use)."""
        # Use the same storage manager instance to ensure consistent database path
        with self.storage.session() as session:
            # Always start with a fresh query
            query = session.query(DatasetDB)
            datasets = query.all()

            # Load examples separately to avoid session issues
            for dataset in datasets:
                try:
                    examples = (
                        session.query(DatasetExampleDB)
                        .filter(DatasetExampleDB.dataset_id == dataset.id)
                        .all()
                    )
                    # Set examples directly on the dataset object
                    dataset.examples = examples
                except Exception as e:
                    logger.warning(
                        f"Failed to load examples for dataset {dataset.name}: {e}"
                    )
                    dataset.examples = []

            return datasets

    def list_datasets(self, name_contains: Optional[str] = None) -> List[DatasetDB]:
        """List datasets with optional name filtering."""
        # Use the same storage manager instance to ensure consistent database path
        with self.storage.session() as session:
            # Always start with a fresh query
            query = session.query(DatasetDB)
            if name_contains:
                query = query.filter(DatasetDB.name.contains(name_contains))

            datasets = query.all()

            # Load examples separately to avoid session issues
            for dataset in datasets:
                try:
                    examples = (
                        session.query(DatasetExampleDB)
                        .filter(DatasetExampleDB.dataset_id == dataset.id)
                        .all()
                    )
                    # Set examples directly on the dataset object
                    dataset.examples = examples
                except Exception as e:
                    logger.warning(
                        f"Failed to load examples for dataset {dataset.name}: {e}"
                    )
                    dataset.examples = []

            return datasets

    def get_dataset(self, name: str) -> Optional[DatasetDB]:
        """Get dataset by name."""
        with self.storage.session() as session:
            return (
                session.query(DatasetDB)
                .options(joinedload(DatasetDB.examples))
                .filter(DatasetDB.name == name)
                .first()
            )

    def create_small_split(
        self,
        dataset_name: str,
        max_items: int = 3,
        split_name: str = "small",
    ) -> int:
        """Manually create a small split for an existing dataset."""
        with self.storage.session() as session:
            dataset = (
                session.query(DatasetDB).filter(DatasetDB.name == dataset_name).first()
            )
            if not dataset:
                raise ValueError(f"Dataset '{dataset_name}' not found")

            # Get all examples in the dataset
            examples = (
                session.query(DatasetExampleDB)
                .filter(DatasetExampleDB.dataset_id == dataset.id)
                .all()
            )

            if not examples:
                logger.warning(f"No examples found in dataset '{dataset_name}'")
                return 0

            # Check if the split already exists
            existing_split = (
                session.query(DatasetExampleDB)
                .filter(
                    DatasetExampleDB.dataset_id == dataset.id,
                    DatasetExampleDB.split == split_name,
                )
                .first()
            )

            if existing_split:
                logger.warning(
                    f"Split '{split_name}' already exists in dataset '{dataset_name}'"
                )
                return 0

            # Take the first max_items examples and create new entries with the new split
            small_examples = examples[:max_items]
            added_count = 0
            examples_to_sync = []

            for example in small_examples:
                # Get next ID for new example
                result = session.execute(
                    text("SELECT COALESCE(MAX(id), 0) + 1 FROM dataset_examples")
                ).fetchone()
                next_example_id = result[0] if result else 1

                # Create new example with new split
                new_example = DatasetExampleDB(
                    id=next_example_id,
                    dataset_id=dataset.id,
                    article_id=example.article_id,
                    inputs=example.inputs,
                    outputs=example.outputs,
                    split=split_name,
                    example_metadata=example.example_metadata,
                )
                session.add(new_example)
                examples_to_sync.append(new_example)
                added_count += 1

            session.flush()  # Get IDs

            # Sync to LangSmith
            if dataset.langsmith_dataset_id and examples_to_sync:
                try:
                    langsmith_example_ids = self.langsmith_sync.add_examples_to_dataset(
                        dataset_id=dataset.langsmith_dataset_id,
                        examples=examples_to_sync,
                    )
                    # Update LangSmith example IDs
                    for i, example in enumerate(examples_to_sync):
                        if i < len(langsmith_example_ids):
                            example.langsmith_example_id = langsmith_example_ids[i]
                    session.commit()
                    logger.info(
                        f"Created '{split_name}' split with {added_count} articles for dataset '{dataset_name}' with LangSmith sync"
                    )
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to sync examples to LangSmith: {e}")
                    raise
            else:
                session.commit()
                logger.info(
                    f"Created '{split_name}' split with {added_count} articles for dataset '{dataset_name}' (local only)"
                )

            return added_count

    def list_articles_in_dataset(
        self,
        dataset_name: str,
        split: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List articles in dataset with optional split filtering."""
        with self.storage.session() as session:
            dataset = (
                session.query(DatasetDB).filter(DatasetDB.name == dataset_name).first()
            )
            if not dataset:
                raise ValueError(f"Dataset '{dataset_name}' not found")

            query = (
                session.query(DatasetExampleDB, ArticleDB)
                .join(ArticleDB)
                .filter(DatasetExampleDB.dataset_id == dataset.id)
            )

            if split:
                # Handle comma-separated splits - find examples that contain the specified split
                query = query.filter(DatasetExampleDB.split.contains(split))

            results = query.all()
            return [
                {
                    "example_id": example.id,
                    "article_id": article.id,
                    "title": article.title,
                    "url": article.url,
                    "split": example.split,
                    "created_at": example.created_at,
                }
                for example, article in results
            ]
