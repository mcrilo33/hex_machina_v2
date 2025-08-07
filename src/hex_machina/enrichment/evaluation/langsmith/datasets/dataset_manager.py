"""Dataset management for LangSmith evaluation datasets."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langsmith import Client, schemas

from ...models.evaluation_models import ContentCompletenessEvaluation
from ..config import LangSmithConfig


class EvaluationDatasetManager:
    """Manager for evaluation datasets in LangSmith."""

    def __init__(
        self, client: Optional[Client] = None, logger: Optional[logging.Logger] = None
    ):
        """Initialize the dataset manager.

        Args:
            client: LangSmith client. If None, creates a new one.
            logger: Optional logger instance.
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.client = client or Client()

    def create_evaluation_dataset(
        self,
        dataset_name: str,
        description: str = "Content completeness evaluation dataset",
    ) -> schemas.Dataset:
        """Create a new evaluation dataset.

        Args:
            dataset_name: Name of the dataset.
            description: Description of the dataset.

        Returns:
            Dataset: The created dataset.
        """
        try:
            dataset = self.client.create_dataset(
                dataset_name=dataset_name,
                description=description,
                data_type=schemas.DataType.kv,
            )

            self.logger.info(f"Created dataset: {dataset_name}")
            return dataset

        except Exception as e:
            self.logger.error(f"Failed to create dataset {dataset_name}: {e}")
            raise

    def add_article_to_dataset(
        self,
        dataset: schemas.Dataset,
        article: Any,
        ground_truth: Optional[Dict[str, Any]] = None,
    ):
        """Add an article to the evaluation dataset.

        Args:
            dataset: The dataset to add the article to.
            article: The article object (ArticleDB or similar).
            ground_truth: Optional ground truth data for the article.
        """
        try:
            # Extract article data - handle both ArticleDB and generic objects
            if hasattr(article, "__table__") and article.__table__.name == "articles":
                # This is an ArticleDB object
                article_data = {
                    "title": article.title,
                    "url": article.url,
                    "content": article.text_content,
                    "content_length": (
                        len(article.text_content) if article.text_content else 0
                    ),
                    "article_id": article.id,
                    "source_url": article.source_url,
                    "url_domain": article.url_domain,
                    "published_date": (
                        article.published_date.isoformat()
                        if article.published_date
                        else None
                    ),
                    "author": article.author,
                    "article_metadata": article.article_metadata,
                    "ingestion_metadata": article.ingestion_metadata,
                    "ingestion_run_id": article.ingestion_run_id,
                    "ingested_at": (
                        article.ingested_at.isoformat() if article.ingested_at else None
                    ),
                    "ingestion_error_status": article.ingestion_error_status,
                    "ingestion_error_message": article.ingestion_error_message,
                    "added_timestamp": datetime.now().isoformat(),
                }
            else:
                # Generic object with fallback attributes
                article_data = {
                    "title": getattr(article, "title", "No title"),
                    "url": getattr(article, "url", "No URL"),
                    "content": getattr(article, "text_content", ""),
                    "content_length": len(getattr(article, "text_content", "")),
                    "article_id": getattr(article, "id", None),
                    "source_url": getattr(article, "source_url", None),
                    "url_domain": getattr(article, "url_domain", None),
                    "published_date": getattr(article, "published_date", None),
                    "author": getattr(article, "author", None),
                    "article_metadata": getattr(article, "article_metadata", None),
                    "ingestion_metadata": getattr(article, "ingestion_metadata", None),
                    "ingestion_run_id": getattr(article, "ingestion_run_id", None),
                    "ingested_at": getattr(article, "ingested_at", None),
                    "ingestion_error_status": getattr(
                        article, "ingestion_error_status", None
                    ),
                    "ingestion_error_message": getattr(
                        article, "ingestion_error_message", None
                    ),
                    "added_timestamp": datetime.now().isoformat(),
                }

            # Add ground truth if provided
            if ground_truth:
                article_data["ground_truth"] = ground_truth
                # Extract requires_manual_review for filtering
                requires_manual_review = ground_truth.get(
                    "requires_manual_review", False
                )
            else:
                requires_manual_review = False

            # Create example
            example = self.client.create_example(
                inputs={
                    "title": article_data["title"],
                    "content": article_data["content"],
                    "url": article_data["url"],
                },
                outputs=ground_truth or {},
                dataset_id=dataset.id,
                metadata={
                    **article_data,
                    "requires_manual_review": requires_manual_review,  # Add as separate metadata field
                    "human_labeled": "false",
                },
            )

            self.logger.debug(
                f"Added article {article_data['url']} to dataset {dataset.name}"
            )
            return example

        except Exception as e:
            self.logger.error(f"Failed to add article to dataset: {e}")
            raise

    def create_test_dataset_from_articles(
        self,
        articles: List[Any],
        dataset_name: Optional[str] = None,
        ground_truth_data: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> schemas.Dataset:
        """Create a test dataset from a list of articles.

        Args:
            articles: List of articles to add to the dataset.
            dataset_name: Name for the dataset. If None, uses default.
            ground_truth_data: Optional ground truth data keyed by article URL.

        Returns:
            Dataset: The created dataset.
        """
        dataset_name = dataset_name or LangSmithConfig.get_dataset_name()

        # Create dataset
        dataset = self.create_evaluation_dataset(
            dataset_name=dataset_name,
            description=f"Test dataset with {len(articles)} articles for content completeness evaluation",
        )

        # Add articles
        for article in articles:
            article_url = getattr(article, "url", "unknown")
            ground_truth = (
                ground_truth_data.get(article_url) if ground_truth_data else None
            )

            self.add_article_to_dataset(dataset, article, ground_truth)

        self.logger.info(
            f"Created test dataset '{dataset_name}' with {len(articles)} articles"
        )
        return dataset

    def list_datasets(self, tags: Optional[List[str]] = None) -> List[schemas.Dataset]:
        """List available datasets.

        Args:
            tags: Optional tags to filter by (not currently supported in LangSmith API).

        Returns:
            List[Dataset]: List of datasets.
        """
        try:
            # Note: tags parameter is not supported in current LangSmith API
            datasets = list(self.client.list_datasets())

            # Filter by tags if provided (client-side filtering)
            if tags:
                filtered_datasets = []
                for dataset in datasets:
                    dataset_tags = getattr(dataset, "tags", []) or []
                    if any(tag in dataset_tags for tag in tags):
                        filtered_datasets.append(dataset)
                datasets = filtered_datasets

            self.logger.info(f"Found {len(datasets)} datasets")
            return datasets

        except Exception as e:
            self.logger.error(f"Failed to list datasets: {e}")
            raise

    def get_dataset(self, dataset_name: str) -> Optional[schemas.Dataset]:
        """Get a dataset by name.

        Args:
            dataset_name: Name of the dataset.

        Returns:
            Dataset: The dataset if found, None otherwise.
        """
        try:
            datasets = self.list_datasets()
            for dataset in datasets:
                if dataset.name == dataset_name:
                    return dataset
            return None

        except Exception as e:
            self.logger.error(f"Failed to get dataset {dataset_name}: {e}")
            raise

    async def run_evaluation_on_dataset(
        self, dataset: schemas.Dataset, evaluator, run_name: Optional[str] = None
    ) -> List[ContentCompletenessEvaluation]:
        """Run evaluation on all examples in a dataset.

        Args:
            dataset: The dataset to evaluate.
            evaluator: The evaluator to use.
            run_name: Name for this evaluation run.

        Returns:
            List[ContentCompletenessEvaluation]: Evaluation results.
        """
        run_name = run_name or LangSmithConfig.get_run_name()
        results = []

        # Get examples from the dataset
        examples = list(self.client.list_examples(dataset_id=dataset.id))

        self.logger.info(
            f"Running evaluation on dataset '{dataset.name}' with {len(examples)} examples"
        )

        for example in examples:
            # Create mock article from example
            mock_article = self._create_mock_article_from_example(example)

            # Evaluate
            result = await evaluator.evaluate_article(mock_article)
            results.append(result)

            # Compare with ground truth if available
            if example.outputs:
                self._compare_with_ground_truth(
                    result, example.outputs, example.inputs.get("url")
                )

        self.logger.info(
            f"Completed evaluation run '{run_name}': {len(results)} results"
        )
        return results

    def _create_mock_article_from_example(self, example) -> Any:
        """Create a mock article object from a dataset example.

        Args:
            example: Dataset example.

        Returns:
            Mock article object with enhanced metadata.
        """

        class MockArticle:
            def __init__(
                self, title: str, content: str, url: str, metadata: dict = None
            ):
                self.title = title
                self.text_content = content
                self.url = url
                self.metadata = metadata or {}

                # Add metadata as attributes for compatibility
                for key, value in self.metadata.items():
                    setattr(self, key, value)

        # Extract metadata from the example
        metadata = example.metadata or {}

        return MockArticle(
            title=example.inputs.get("title", "No title"),
            content=example.inputs.get("content", ""),
            url=example.inputs.get("url", "No URL"),
            metadata=metadata,
        )

    def _compare_with_ground_truth(
        self,
        result: ContentCompletenessEvaluation,
        ground_truth: Dict[str, Any],
        article_url: str,
    ):
        """Compare evaluation result with ground truth.

        Args:
            result: The evaluation result.
            ground_truth: The ground truth data.
            article_url: URL of the article.
        """
        if "is_complete" in ground_truth:
            expected = ground_truth["is_complete"]
            actual = result.is_complete

            if expected != actual:
                self.logger.warning(
                    f"Ground truth mismatch for {article_url}: "
                    f"expected {expected}, got {actual}"
                )
            else:
                self.logger.debug(f"Ground truth match for {article_url}: {actual}")
