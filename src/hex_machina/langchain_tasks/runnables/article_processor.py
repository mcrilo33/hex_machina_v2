"""ArticleProcessor runnable for processing individual articles with tracing."""

import logging
from typing import Any, Dict, Optional

from langchain_core.runnables import Runnable
from langsmith import traceable


@traceable(name="ArticleProcessor", run_type="tool")
class ArticleProcessor(Runnable):
    """LangChain runnable that processes individual articles with proper tracing."""

    def __init__(self, processor_type: str, config: Dict[str, Any]):
        """Initialize ArticleProcessor.

        Args:
            processor_type: Type of processing (e.g., "summarize", "extract_keywords")
            config: Configuration for the processor
        """
        self.processor_type = processor_type
        self.config = config
        self._logger = logging.getLogger(f"runnable.ArticleProcessor.{processor_type}")

    def invoke(
        self, inputs: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a single article.

        Args:
            inputs: Dictionary containing article data (from RunnableParallel)
            config: Optional configuration override

        Returns:
            Processed article data
        """
        try:
            # When used in RunnableParallel, inputs will be the article directly
            # When used standalone, inputs will have "article" key
            if "id" in inputs and "title" in inputs:
                # Direct article input (from RunnableParallel)
                article = inputs
            else:
                # Wrapped article input (standalone usage)
                article = inputs.get("article", {})

            article_id = article.get("id")

            self._logger.info(
                f"Processing article {article_id} with {self.processor_type}"
            )

            if self.processor_type == "summarize":
                result = self._generate_summary(article)
            elif self.processor_type == "extract_keywords":
                result = self._extract_keywords(article)
            else:
                raise ValueError(f"Unknown processor type: {self.processor_type}")

            # Return processed result with article context
            return {
                "article_id": article_id,
                "article_title": article.get("title", "Unknown"),
                "processor_type": self.processor_type,
                "result": result,
                "original_article": article,
            }

        except Exception as e:
            self._logger.error(f"Failed to process article: {e}")
            raise

    def _generate_summary(self, article: Dict[str, Any]) -> str:
        """Generate a summary for an article."""
        title = article.get("title", "Unknown Title")
        summary_length = self.config.get("summary_length", "short")

        # Mock summary generation (replace with real LLM call)
        if summary_length == "short":
            return f"Brief summary of: {title}"
        else:
            return f"Detailed analysis of: {title} - This article covers important topics and provides valuable insights."

    def _extract_keywords(self, article: Dict[str, Any]) -> list[str]:
        """Extract keywords from an article."""
        title = article.get("title", "")
        text_content = article.get("text_content", "")
        max_keywords = self.config.get("max_keywords", 5)

        # Mock keyword extraction (replace with real LLM call)
        # Simple keyword detection based on common terms
        common_keywords = [
            "AI",
            "machine learning",
            "technology",
            "business",
            "innovation",
            "data",
            "research",
        ]
        detected_keywords = [
            kw
            for kw in common_keywords
            if kw.lower() in (title + " " + text_content).lower()
        ]

        # Return detected keywords or fallback
        if detected_keywords:
            return detected_keywords[:max_keywords]
        else:
            return ["technology", "innovation", "development"][:max_keywords]
