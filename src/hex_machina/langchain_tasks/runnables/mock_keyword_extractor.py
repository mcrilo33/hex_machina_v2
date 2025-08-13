"""Mock keyword extractor runnable for testing custom runnables."""

import logging
import random
from typing import Any, Dict, List, Optional

from langchain_core.runnables import Runnable


class MockKeywordExtractor(Runnable):
    """Mock runnable that generates fake keywords for articles."""

    def __init__(self, max_keywords: int = 5):
        """Initialize MockKeywordExtractor.

        Args:
            max_keywords: Maximum number of keywords to generate
        """
        self.max_keywords = max_keywords
        self._logger = logging.getLogger("runnable.MockKeywordExtractor")

        # Mock keyword pool for different topics
        self.keyword_pools = {
            "tech": [
                "AI",
                "machine learning",
                "technology",
                "innovation",
                "digital",
                "automation",
                "data",
                "cloud",
                "software",
                "hardware",
            ],
            "business": [
                "strategy",
                "leadership",
                "management",
                "growth",
                "market",
                "finance",
                "startup",
                "entrepreneurship",
                "investment",
                "strategy",
            ],
            "science": [
                "research",
                "discovery",
                "experiment",
                "analysis",
                "theory",
                "hypothesis",
                "observation",
                "methodology",
                "results",
                "conclusion",
            ],
            "general": [
                "development",
                "progress",
                "future",
                "impact",
                "solution",
                "challenge",
                "opportunity",
                "transformation",
                "evolution",
                "breakthrough",
            ],
        }

    def invoke(
        self, inputs: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate mock keywords for articles.

        Args:
            inputs: Input dictionary containing articles and summaries

        Returns:
            Input dictionary with added keywords
        """
        try:
            # Handle both dict and list inputs
            if isinstance(inputs, dict):
                articles = inputs.get("fetch_sample_articles", [])
            elif isinstance(inputs, list):
                articles = inputs
            else:
                articles = []

            if not articles:
                self._logger.warning("No articles found to extract keywords from")
                return inputs if isinstance(inputs, dict) else {"articles": []}

            # Generate mock keywords for each article
            keywords_list = []
            for article in articles:
                article_id = article.get("id")
                title = article.get("title", "")
                text_content = article.get("text_content", "")

                # Determine topic based on content
                topic = self._detect_topic(title, text_content)

                # Generate keywords
                keywords = self._generate_mock_keywords(topic, self.max_keywords)

                keywords_list.append(
                    {"article_id": article_id, "title": title, "keywords": keywords}
                )

            # Create result structure
            result = {
                "extract_keywords": {
                    "keywords_list": keywords_list,
                    "keywords": keywords_list,  # For compatibility with input_mapping
                }
            }

            # If inputs was a dict, merge with it
            if isinstance(inputs, dict):
                result.update(inputs)

            self._logger.info(f"Generated keywords for {len(keywords_list)} articles")
            return result

        except Exception as e:
            self._logger.error(f"Failed to extract keywords: {e}")
            raise

    def _detect_topic(self, title: str, text_content: str) -> str:
        """Detect the topic of an article based on title and content.

        Args:
            title: Article title
            text_content: Article text content

        Returns:
            Detected topic ("tech", "business", "science", or "general")
        """
        content = (title + " " + text_content).lower()

        if any(
            word in content
            for word in ["ai", "machine learning", "technology", "software", "digital"]
        ):
            return "tech"
        elif any(
            word in content
            for word in ["business", "market", "finance", "startup", "strategy"]
        ):
            return "business"
        elif any(
            word in content
            for word in ["research", "study", "experiment", "analysis", "theory"]
        ):
            return "science"
        else:
            return "general"

    def _generate_mock_keywords(self, topic: str, max_count: int) -> List[str]:
        """Generate mock keywords for a given topic.

        Args:
            topic: Topic category
            max_count: Maximum number of keywords to generate

        Returns:
            List of generated keywords
        """
        pool = self.keyword_pools.get(topic, self.keyword_pools["general"])

        # Randomly select keywords from the pool
        num_keywords = min(max_count, len(pool))
        selected_keywords = random.sample(pool, num_keywords)

        return selected_keywords
