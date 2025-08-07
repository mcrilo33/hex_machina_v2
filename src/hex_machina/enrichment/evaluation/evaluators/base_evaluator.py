"""Base evaluator interface for content completeness evaluation."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from src.hex_machina.enrichment.evaluation.models.evaluation_models import (
    ContentCompletenessEvaluation,
    EvaluationStatus,
)


class BaseEvaluator(ABC):
    """Abstract base class for content completeness evaluators."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the evaluator.

        Args:
            logger: Optional logger instance. If None, creates a default logger.
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def evaluate_article(
        self, article: Any, **kwargs
    ) -> ContentCompletenessEvaluation:
        """Evaluate a single article for content completeness.

        Args:
            article: The article object to evaluate. Expected to have attributes
                    like 'url', 'text_content', 'title', etc.
            **kwargs: Additional arguments for evaluation.

        Returns:
            ContentCompletenessEvaluation: The evaluation result.

        Raises:
            Exception: If evaluation fails.
        """
        pass

    @abstractmethod
    async def evaluate_articles(
        self, articles: list[Any], **kwargs
    ) -> list[ContentCompletenessEvaluation]:
        """Evaluate multiple articles for content completeness.

        Args:
            articles: List of article objects to evaluate.
            **kwargs: Additional arguments for evaluation.

        Returns:
            list[ContentCompletenessEvaluation]: List of evaluation results.
        """
        pass

    def _create_error_evaluation(
        self, article: Any, error_message: str
    ) -> ContentCompletenessEvaluation:
        """Create an error evaluation result when evaluation fails.

        Args:
            article: The article that failed evaluation.
            error_message: Description of the error.

        Returns:
            ContentCompletenessEvaluation: Error evaluation result.
        """
        return ContentCompletenessEvaluation(
            article_id=(
                str(getattr(article, "id", None))
                if getattr(article, "id", None) is not None
                else None
            ),
            url=getattr(article, "url", "unknown"),
            is_complete=False,
            detected_issues=["evaluation_error"],
            evaluation_status=EvaluationStatus.FAILED,
            error_message=error_message,
        )

    def _extract_article_text(self, article: Any) -> str:
        """Extract text content from article object.

        Args:
            article: The article object.

        Returns:
            str: Extracted text content.
        """
        # Try different possible attribute names for text content
        text_attributes = ["text_content", "content", "body", "text"]

        for attr in text_attributes:
            if hasattr(article, attr):
                content = getattr(article, attr)
                if content and isinstance(content, str):
                    return content.strip()

        # Fallback: try to get any string-like content
        for attr in dir(article):
            if not attr.startswith("_"):
                value = getattr(article, attr)
                if (
                    isinstance(value, str) and len(value) > 100
                ):  # Reasonable content length
                    return value.strip()

        return ""

    def _extract_article_title(self, article: Any) -> str:
        """Extract title from article object.

        Args:
            article: The article object.

        Returns:
            str: Extracted title.
        """
        title_attributes = ["title", "headline", "name"]

        for attr in title_attributes:
            if hasattr(article, attr):
                title = getattr(article, attr)
                if title and isinstance(title, str):
                    return title.strip()

        return ""

    def _extract_article_url(self, article: Any) -> str:
        """Extract URL from article object.

        Args:
            article: The article object.

        Returns:
            str: Extracted URL.
        """
        url_attributes = ["url", "link", "href"]

        for attr in url_attributes:
            if hasattr(article, attr):
                url = getattr(article, attr)
                if url and isinstance(url, str):
                    return url.strip()

        return ""
