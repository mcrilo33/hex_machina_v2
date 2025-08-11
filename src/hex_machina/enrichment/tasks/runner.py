"""Task runner for enrichment tasks."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

from src.hex_machina.core.base import TaskInput, TaskOutput
from src.hex_machina.enrichment.config.database_config import database_config_manager
from src.hex_machina.enrichment.config.task_configs import task_config_manager
from src.hex_machina.enrichment.core.article_source import ArticleSource
from src.hex_machina.enrichment.core.registry import task_registry
from src.hex_machina.enrichment.storage.database import DatabaseEnrichmentStorage
from src.hex_machina.enrichment.storage.task_storage import task_storage
from src.hex_machina.enrichment.tracing.langsmith_integration import (
    get_langsmith_tracer,
)
from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB


class TaskRunner:
    """Unified task runner for enrichment tasks."""

    def __init__(self):
        self._logger = logging.getLogger("enrichment.task.runner")
        self._task_registry = task_registry
        self._task_storage = task_storage
        self._database_storage = DatabaseEnrichmentStorage()
        self._article_source = ArticleSource()
        self._langsmith_tracer = get_langsmith_tracer()
        self._task_config_manager = task_config_manager

    async def run_task(
        self,
        task_name: str,
        input_data: Dict[str, Any],
        workflow_operation_id: Optional[str] = None,
        task_config: Optional[Dict[str, Any]] = None,
        save_to_db: Optional[bool] = None,
    ) -> TaskOutput:
        """Run a single task on input data."""
        self._logger.info(f"Running task: {task_name}")

        # Generate task ID that is coherent with workflow_operation_id
        import uuid

        # Every task should have a workflow_operation_id
        # The CLI now always provides one, but keep fallback for backward compatibility
        if not workflow_operation_id:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            short_uuid = uuid.uuid4().hex[:8]
            workflow_operation_id = f"{task_name}_standalone_{timestamp}_{short_uuid}"
            self._logger.info(
                f"Generated standalone workflow operation ID: {workflow_operation_id}"
            )

        # Create task ID that is part of the workflow operation
        task_id = f"{workflow_operation_id}_task_{uuid.uuid4().hex[:8]}"

        # Detect article context for database saving
        article_context = self._detect_article_context(input_data)

        # Determine if we should save to database
        # Use provided save_to_db if specified, otherwise use default behavior
        if save_to_db is not None:
            should_save = save_to_db
        else:
            should_save = self._should_save_to_db(input_data)

        # Create task input
        task_input = TaskInput(
            task_id=task_id,
            task_name=task_name,
            input_data=input_data,
            save_to_db=should_save,
            article_id=article_context.get("article_id") if article_context else None,
            workflow_operation_id=workflow_operation_id,
        )

        # Load task configuration
        if task_config:
            # Use dynamic configuration
            yaml_config = task_config
            langchain_config = self._task_config_manager.create_langchain_config(
                yaml_config
            )
        else:
            # Use default configuration
            yaml_config = self._task_config_manager.load_config(task_name)
            langchain_config = self._task_config_manager.create_langchain_config(
                yaml_config
            )

        # Create task instance
        task = self._task_registry.create_task(task_name, config=langchain_config)
        if not task:
            raise Exception(f"Failed to create task: {task_name}")

        # Initialize task
        task.initialize()

        # Execute task with tracing
        result = await self._langsmith_tracer.execute_task_with_tracing(
            task, task_input, task_name
        )

        # Add task input to result metadata for database saving
        if result.metadata is None:
            result.metadata = {}
        result.metadata["task_input"] = task_input.model_dump()

        # Save results only if save_to_db is True
        if should_save:
            await self._save_results(task_input, result)
        else:
            self._logger.info("Database saving is disabled for this task")

        return result

    async def run_task_on_articles(
        self,
        task_name: str,
        articles: List[ArticleDB],
        batch_size: int = 10,
        max_concurrent: int = 3,
        skip_existing: bool = False,
        task_config: Optional[Dict[str, Any]] = None,
        workflow_operation_id: Optional[str] = None,
        save_to_db: Optional[bool] = None,
    ) -> List[TaskOutput]:
        """Run a task on multiple articles with batch processing."""
        self._logger.info(f"Running task {task_name} on {len(articles)} articles")

        # Use provided workflow operation ID or generate one for this batch run
        if not workflow_operation_id:
            import uuid
            from datetime import datetime

            # Create a workflow operation ID for this batch run
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            short_uuid = uuid.uuid4().hex[:8]
            workflow_operation_id = f"{task_name}_{timestamp}_{short_uuid}"
            self._logger.info(
                f"Generated workflow operation ID: {workflow_operation_id}"
            )
        else:
            self._logger.info(
                f"Using provided workflow operation ID: {workflow_operation_id}"
            )

        results = []

        # Process in batches
        for i in range(0, len(articles), batch_size):
            batch = articles[i : i + batch_size]
            self._logger.info(
                f"Processing batch {i//batch_size + 1}/{(len(articles) + batch_size - 1)//batch_size}"
            )

            # Create tasks for this batch
            tasks = []
            for article in batch:
                if skip_existing and self._is_article_processed(task_name, article.id):
                    self._logger.debug(
                        f"Skipping already processed article {article.id}"
                    )
                    continue

                input_data = self._article_to_input_data(article)
                # Create the coroutine (don't await it yet) with workflow operation ID and task config
                task_coro = self.run_task(
                    task_name,
                    input_data,
                    workflow_operation_id,
                    task_config,
                    save_to_db,
                )
                tasks.append(task_coro)

            # Execute batch concurrently
            if tasks:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend(
                    [r for r in batch_results if not isinstance(r, Exception)]
                )

                # Log any exceptions
                exceptions = [r for r in batch_results if isinstance(r, Exception)]
                for exc in exceptions:
                    self._logger.error(f"Task execution error: {exc}")

        self._logger.info(f"Completed task {task_name} on {len(articles)} articles")
        return results

    async def run_task_on_source(
        self,
        task_name: str,
        source_type: str,
        source_value: Union[int, str, List[int]],
        batch_size: int = 10,
        max_concurrent: int = 3,
        skip_existing: bool = False,
        limit: Optional[int] = None,
        task_config: Optional[Dict[str, Any]] = None,
        workflow_operation_id: Optional[str] = None,
        save_to_db: Optional[bool] = None,
    ) -> List[TaskOutput]:
        """Run a task on articles from a specific source."""
        self._logger.info(
            f"Running task {task_name} on source: {source_type}={source_value}"
        )

        # Resolve articles from source
        articles = self._resolve_articles_from_source(source_type, source_value, limit)

        if not articles:
            self._logger.warning(
                f"No articles found for source: {source_type}={source_value}"
            )
            return []

        # Run task on articles
        return await self.run_task_on_articles(
            task_name=task_name,
            articles=articles,
            batch_size=batch_size,
            max_concurrent=max_concurrent,
            skip_existing=skip_existing,
            task_config=task_config,
            workflow_operation_id=workflow_operation_id,
            save_to_db=save_to_db,
        )

    def _resolve_articles_from_source(
        self,
        source_type: str,
        source_value: Union[int, str, List[int]],
        limit: Optional[int] = None,
    ) -> List[ArticleDB]:
        """Resolve articles from a specific source."""
        if source_type == "single_article":
            article = self._article_source.resolve_single_article(source_value)
            return [article] if article else []
        elif source_type == "multiple_articles":
            return self._article_source.resolve_multiple_articles(source_value)
        elif source_type == "ingestion_operation":
            articles = self._article_source.resolve_ingestion_operation(source_value)
        elif source_type == "dataset":
            articles = self._article_source.resolve_dataset(source_value)
        elif source_type == "all_articles":
            articles = self._article_source.resolve_all_articles(limit)
        else:
            self._logger.error(f"Unknown source type: {source_type}")
            return []

        if limit and len(articles) > limit:
            articles = articles[:limit]

        return articles

    def _article_to_input_data(self, article: ArticleDB) -> Dict[str, Any]:
        """Convert ArticleDB to input data format."""
        return {
            "id": article.id,
            "title": article.title,
            "url": article.url,
            "domain": article.url_domain,
            "content": article.text_content,
            "url_domain": article.url_domain,  # Keep both for compatibility
        }

    def _should_save_to_db(self, input_data: Dict[str, Any]) -> bool:
        """Determine if results should be saved to database."""
        # Check if this is a database article
        article_context = self._detect_article_context(input_data)
        if article_context:
            return database_config_manager.get_enable_by_default()
        return False

    def _is_article_processed(self, task_name: str, article_id: int) -> bool:
        """Check if an article has already been processed by this task."""
        try:
            # Check database for existing enrichment
            with self._database_storage._storage_manager.session() as session:
                existing = (
                    session.query(self._database_storage._EnrichmentDB)
                    .filter(
                        self._database_storage._EnrichmentDB.article_id == article_id,
                        self._database_storage._EnrichmentDB.tool_name == task_name,
                    )
                    .first()
                )
                return existing is not None
        except Exception as e:
            self._logger.warning(
                f"Error checking if article {article_id} is processed: {e}"
            )
            return False

    async def _save_results(self, task_input: TaskInput, result: TaskOutput):
        """Save task results to storage."""
        try:
            # Save to local storage
            self._task_storage.store_task_input(task_input)
            self._task_storage.store_task_output(result)

            # Save to database if needed
            if task_input.save_to_db and result.error is None:
                self._database_storage.store_task_output(result)

        except Exception as e:
            self._logger.error(f"Error saving results: {e}")

    def _detect_article_context(
        self, input_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Detect if input data contains article context from database."""
        # Check for direct article ID
        if "id" in input_data:
            article = self._find_article_by_id(input_data["id"])
            if article:
                return {"article_id": article.id, "source": "database"}

        # Check for URL
        if "url" in input_data:
            article = self._find_article_by_url(input_data["url"])
            if article:
                return {"article_id": article.id, "source": "database"}

        # Check for title and domain
        if "title" in input_data and "domain" in input_data:
            article = self._find_article_by_title_domain(
                input_data["title"], input_data["domain"]
            )
            if article:
                return {"article_id": article.id, "source": "database"}

        # Check for url_domain (alternative field name)
        if "title" in input_data and "url_domain" in input_data:
            article = self._find_article_by_title_domain(
                input_data["title"], input_data["url_domain"]
            )
            if article:
                return {"article_id": article.id, "source": "database"}

        return None

    def _find_article_by_id(self, article_id: int) -> Optional[ArticleDB]:
        """Find article by ID in database."""
        try:
            db_path = database_config_manager.get_db_path()
            self._logger.debug(
                f"Looking up article ID {article_id} in database: {db_path}"
            )

            storage_manager = get_storage_manager(db_path)
            with storage_manager.session() as session:
                article = (
                    session.query(ArticleDB).filter(ArticleDB.id == article_id).first()
                )
                if article:
                    self._logger.debug(
                        f"Found article by ID {article_id}: {article.title}"
                    )
                else:
                    self._logger.debug(f"No article found by ID {article_id}")
                return article
        except Exception as e:
            self._logger.error(f"Error finding article by ID {article_id}: {e}")
            return None

    def _find_article_by_url(self, url: str) -> Optional[ArticleDB]:
        """Find article by URL in database."""
        try:
            db_path = database_config_manager.get_db_path()
            storage_manager = get_storage_manager(db_path)
            with storage_manager.session() as session:
                return session.query(ArticleDB).filter(ArticleDB.url == url).first()
        except Exception as e:
            self._logger.error(f"Error finding article by URL {url}: {e}")
            return None

    def _find_article_by_title_domain(
        self, title: str, domain: str
    ) -> Optional[ArticleDB]:
        """Find article by title and domain in database."""
        try:
            db_path = database_config_manager.get_db_path()
            storage_manager = get_storage_manager(db_path)
            with storage_manager.session() as session:
                return (
                    session.query(ArticleDB)
                    .filter(ArticleDB.title == title, ArticleDB.url_domain == domain)
                    .first()
                )
        except Exception as e:
            self._logger.error(
                f"Error finding article by title/domain {title}/{domain}: {e}"
            )
            return None


# Global task runner instance
task_runner = TaskRunner()
