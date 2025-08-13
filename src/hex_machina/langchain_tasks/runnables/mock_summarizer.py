"""MockSummarizer runnable for generating fake article summaries."""

import logging
from typing import Any, Dict, Optional

from langchain_core.runnables import Runnable
from langsmith import traceable


class MockSummarizer(Runnable):
    """Mock runnable that generates fake article summaries."""

    def __init__(self, summary_length: str = "short"):
        """Initialize MockSummarizer.

        Args:
            summary_length: Length of summary to generate ("short", "medium", "long")
        """
        self.summary_length = summary_length
        self._logger = logging.getLogger("runnable.MockSummarizer")

    @traceable(name="MockSummarizer", run_type="tool")
    def invoke(
        self, inputs: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate mock summaries for articles.

        Args:
            inputs: Input dictionary or direct article (when used with .map())
            config: Optional configuration override

        Returns:
            Input dictionary with added summaries
        """
        try:
            # Handle different input formats:
            # 1. Direct article input (from .map() operation)
            # 2. Wrapped article input (standalone usage)
            # 3. List of articles (legacy usage)

            if "id" in inputs and "title" in inputs:
                # Direct article input from .map() - this is what we want!
                articles = [inputs]
            elif isinstance(inputs, dict) and "fetch_sample_articles" in inputs:
                # Wrapped input with fetch_sample_articles key
                articles = inputs.get("fetch_sample_articles", [])
            elif isinstance(inputs, list):
                # Direct list of articles
                articles = inputs
            else:
                articles = []

            if not articles:
                self._logger.warning("No articles found to summarize")
                return inputs if isinstance(inputs, dict) else {"articles": []}

            # Generate mock summaries
            summaries = []
            for article in articles:
                title = article.get("title", "Unknown Title")
                summary = self._generate_mock_summary(title, self.summary_length)
                summaries.append(
                    {
                        "article_id": article.get("id"),
                        "title": title,
                        "summary": summary,
                    }
                )

            # Create result structure
            result = {
                "generate_article_summary": {
                    "summaries": summaries,
                    "summary": (
                        summaries[0]["summary"] if summaries else "No summary generated"
                    ),  # Flatten for input_mapping
                }
            }

            # If inputs was a dict, merge with it (but avoid duplicate keys)
            if isinstance(inputs, dict):
                # Only merge non-conflicting keys
                for key, value in inputs.items():
                    if key not in result:
                        result[key] = value

            self._logger.info(f"Generated {len(summaries)} mock summaries")
            return result

        except Exception as e:
            self._logger.error(f"Failed to generate summaries: {e}")
            raise

    def _generate_mock_summary(self, title: str, length: str) -> str:
        """Generate a mock summary based on title and length.

        Args:
            title: Article title
            length: Desired summary length

        Returns:
            Mock summary text
        """
        if length == "short":
            return f"This is a brief summary of: {title}"
        elif length == "medium":
            return f"This article discusses {title}. It provides insights and analysis on the topic."
        else:  # long
            return f"This comprehensive article explores {title}. It covers various aspects, provides detailed analysis, and offers valuable insights for readers interested in this subject matter."
