"""Dataset manager for handling dataset operations with LangSmith sync."""

import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text

from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import DatasetDB, DatasetExampleDB, ArticleDB, EnrichmentDB
from .langsmith_sync import LangSmithSync
from .evaluators import BooleanEvaluator

logger = logging.getLogger(__name__)


class DatasetManager:
    """Manages datasets with automatic LangSmith synchronization."""

    def __init__(self):
        """Initialize the dataset manager."""
        self.storage = get_storage_manager()
        self.langsmith_sync = LangSmithSync()

    def create_dataset(
        self,
        name: str,
        description: Optional[str] = None,
        data_type: str = "kv",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DatasetDB:
        """Create a new dataset with automatic LangSmith sync."""
        with self.storage.session() as session:
            # Check if dataset already exists
            existing = session.query(DatasetDB).filter(DatasetDB.name == name).first()
            if existing:
                raise ValueError(f"Dataset '{name}' already exists")

            # Get next ID for dataset
            result = session.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM datasets")).fetchone()
            next_id = result[0] if result else 1
            
            # Create dataset
            dataset = DatasetDB(
                id=next_id,
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

    def add_articles_to_dataset(
        self,
        dataset_name: str,
        article_ids: List[int],
        split: str = "train",
        inputs_template: Optional[Dict[str, Any]] = None,
        outputs_template: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Add articles to dataset with automatic LangSmith sync."""
        with self.storage.session() as session:
            dataset = session.query(DatasetDB).filter(DatasetDB.name == dataset_name).first()
            if not dataset:
                raise ValueError(f"Dataset '{dataset_name}' not found")

            # Get articles
            articles = session.query(ArticleDB).filter(ArticleDB.id.in_(article_ids)).all()
            if len(articles) != len(article_ids):
                found_ids = {article.id for article in articles}
                missing_ids = set(article_ids) - found_ids
                raise ValueError(f"Articles not found: {missing_ids}")

            added_count = 0
            examples_to_sync = []

            for article in articles:
                # Check if example already exists
                existing = session.query(DatasetExampleDB).filter(
                    DatasetExampleDB.dataset_id == dataset.id,
                    DatasetExampleDB.article_id == article.id,
                    DatasetExampleDB.split == split,
                ).first()

                if existing:
                    logger.warning(f"Article {article.id} already in dataset '{dataset_name}' split '{split}'")
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
                result = session.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM dataset_examples")).fetchone()
                next_example_id = result[0] if result else 1
                
                # Create example
                example = DatasetExampleDB(
                    id=next_example_id,
                    dataset_id=dataset.id,
                    article_id=article.id,
                    inputs=inputs,
                    outputs=outputs,
                    split=split,
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
                    self.langsmith_sync.add_examples_to_dataset(
                        dataset_id=dataset.langsmith_dataset_id,
                        examples=examples_to_sync,
                    )
                    # Update LangSmith example IDs
                    for example in examples_to_sync:
                        # Note: In a real implementation, you'd get the actual LangSmith example ID
                        # For now, we'll use a placeholder
                        example.langsmith_example_id = f"langsmith_{example.id}"
                    session.commit()
                    logger.info(f"Added {added_count} articles to dataset '{dataset_name}' with LangSmith sync")
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
            articles = session.query(ArticleDB).join(EnrichmentDB).filter(
                EnrichmentDB.workflow_operation_id == workflow_operation_id
            ).distinct().all()

            if not articles:
                raise ValueError(f"No articles found for workflow operation '{workflow_operation_id}'")

            # Create dataset
            dataset = self.create_dataset(
                name=name,
                description=description or f"Dataset from workflow operation {workflow_operation_id}",
            )

            # Add articles
            article_ids = [article.id for article in articles]
            self.add_articles_to_dataset(name, article_ids, split)

            return dataset

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
            articles = session.query(ArticleDB).filter(
                ArticleDB.ingestion_run_id == ingestion_operation_id
            ).all()

            if not articles:
                raise ValueError(f"No articles found for ingestion operation {ingestion_operation_id}")

            # Create dataset
            dataset = self.create_dataset(
                name=name,
                description=description or f"Dataset from ingestion operation {ingestion_operation_id}",
            )

            # Add articles
            article_ids = [article.id for article in articles]
            self.add_articles_to_dataset(name, article_ids, split)

            return dataset

    def apply_evaluator_for_split(
        self,
        dataset_name: str,
        evaluator: BooleanEvaluator,
        criteria: Dict[str, Any],
        output_split: str,
    ) -> int:
        """Apply boolean evaluator to create custom split."""
        with self.storage.session() as session:
            dataset = session.query(DatasetDB).filter(DatasetDB.name == dataset_name).first()
            if not dataset:
                raise ValueError(f"Dataset '{dataset_name}' not found")

            # Get all examples
            examples = session.query(DatasetExampleDB).filter(
                DatasetExampleDB.dataset_id == dataset.id
            ).all()

            moved_count = 0
            examples_to_sync = []

            for example in examples:
                article = session.query(ArticleDB).filter(ArticleDB.id == example.article_id).first()
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
                    logger.info(f"Moved {moved_count} examples to split '{output_split}' with LangSmith sync")
                except Exception as e:
                    logger.error(f"Failed to sync split changes to LangSmith: {e}")
                    # Don't rollback, just commit the local changes
                    session.commit()
                    logger.info(f"Moved {moved_count} examples to split '{output_split}' (local only)")

            return moved_count

    def list_datasets(self, name_contains: Optional[str] = None) -> List[DatasetDB]:
        """List datasets with optional name filtering."""
        with self.storage.session() as session:
            query = session.query(DatasetDB).options(joinedload(DatasetDB.examples))
            if name_contains:
                query = query.filter(DatasetDB.name.contains(name_contains))
            return query.all()

    def get_dataset(self, name: str) -> Optional[DatasetDB]:
        """Get dataset by name."""
        with self.storage.session() as session:
            return session.query(DatasetDB).options(joinedload(DatasetDB.examples)).filter(DatasetDB.name == name).first()

    def delete_dataset(self, name: str) -> bool:
        """Delete dataset with LangSmith sync."""
        with self.storage.session() as session:
            dataset = session.query(DatasetDB).filter(DatasetDB.name == name).first()
            if not dataset:
                return False

            # Delete from LangSmith
            if dataset.langsmith_dataset_id:
                try:
                    self.langsmith_sync.delete_dataset(dataset.langsmith_dataset_id)
                except Exception as e:
                    logger.error(f"Failed to delete dataset from LangSmith: {e}")

            # Delete from local database
            session.delete(dataset)
            session.commit()
            logger.info(f"Deleted dataset '{name}'")
            return True

    def list_articles_in_dataset(
        self,
        dataset_name: str,
        split: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List articles in dataset with optional split filtering."""
        with self.storage.session() as session:
            dataset = session.query(DatasetDB).filter(DatasetDB.name == dataset_name).first()
            if not dataset:
                raise ValueError(f"Dataset '{dataset_name}' not found")

            query = session.query(DatasetExampleDB, ArticleDB).join(ArticleDB).filter(
                DatasetExampleDB.dataset_id == dataset.id
            )

            if split:
                query = query.filter(DatasetExampleDB.split == split)

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