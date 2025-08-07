"""Boolean evaluators for creating custom dataset splits."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from src.hex_machina.storage.models import ArticleDB


class BooleanEvaluator(ABC):
    """Base class for boolean evaluators that create custom splits."""

    @abstractmethod
    def evaluate(self, article: ArticleDB, criteria: Dict[str, Any]) -> bool:
        """Evaluate if article meets criteria for split inclusion."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get evaluator name for CLI."""
        pass

    def get_description(self) -> str:
        """Get evaluator description."""
        return f"Boolean evaluator: {self.get_name()}"


class ContentCompletenessEvaluator(BooleanEvaluator):
    """Evaluator for content completeness criteria."""

    def evaluate(self, article: ArticleDB, criteria: Dict[str, Any]) -> bool:
        """Check if article has complete content based on criteria."""
        if not article.text_content:
            return False

        # Check minimum length
        min_length = criteria.get("min_length", 1000)
        if len(article.text_content) < min_length:
            return False

        # Check for truncation indicators
        truncation_indicators = criteria.get("truncation_indicators", [
            "...", "[truncated]", "[continued]", "read more"
        ])
        
        text_lower = article.text_content.lower()
        for indicator in truncation_indicators:
            if indicator.lower() in text_lower:
                return False

        # Check for minimum word count
        min_words = criteria.get("min_words", 100)
        word_count = len(article.text_content.split())
        if word_count < min_words:
            return False

        return True

    def get_name(self) -> str:
        return "content_completeness"


class DomainFilterEvaluator(BooleanEvaluator):
    """Evaluator for domain-based filtering."""

    def evaluate(self, article: ArticleDB, criteria: Dict[str, Any]) -> bool:
        """Check if article domain matches criteria."""
        if not article.url_domain:
            return False

        # Check allowed domains
        allowed_domains = criteria.get("domains", [])
        if allowed_domains and article.url_domain not in allowed_domains:
            return False

        # Check excluded domains
        excluded_domains = criteria.get("excluded_domains", [])
        if excluded_domains and article.url_domain in excluded_domains:
            return False

        return True

    def get_name(self) -> str:
        return "domain_filter"


class ArticleLengthEvaluator(BooleanEvaluator):
    """Evaluator for article length criteria."""

    def evaluate(self, article: ArticleDB, criteria: Dict[str, Any]) -> bool:
        """Check if article length meets criteria."""
        if not article.text_content:
            return False

        text_length = len(article.text_content)
        word_count = len(article.text_content.split())

        # Check minimum length
        min_length = criteria.get("min_length")
        if min_length and text_length < min_length:
            return False

        # Check maximum length
        max_length = criteria.get("max_length")
        if max_length and text_length > max_length:
            return False

        # Check minimum word count
        min_words = criteria.get("min_words")
        if min_words and word_count < min_words:
            return False

        # Check maximum word count
        max_words = criteria.get("max_words")
        if max_words and word_count > max_words:
            return False

        return True

    def get_name(self) -> str:
        return "article_length"


class DateRangeEvaluator(BooleanEvaluator):
    """Evaluator for date range criteria."""

    def evaluate(self, article: ArticleDB, criteria: Dict[str, Any]) -> bool:
        """Check if article date is within specified range."""
        if not article.published_date:
            return False

        from datetime import datetime

        # Check start date
        start_date_str = criteria.get("start_date")
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
            if article.published_date < start_date:
                return False

        # Check end date
        end_date_str = criteria.get("end_date")
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
            if article.published_date > end_date:
                return False

        return True

    def get_name(self) -> str:
        return "date_range"


class TitleKeywordEvaluator(BooleanEvaluator):
    """Evaluator for title keyword criteria."""

    def evaluate(self, article: ArticleDB, criteria: Dict[str, Any]) -> bool:
        """Check if article title contains specified keywords."""
        if not article.title:
            return False

        title_lower = article.title.lower()

        # Check required keywords (all must be present)
        required_keywords = criteria.get("required_keywords", [])
        for keyword in required_keywords:
            if keyword.lower() not in title_lower:
                return False

        # Check excluded keywords (none should be present)
        excluded_keywords = criteria.get("excluded_keywords", [])
        for keyword in excluded_keywords:
            if keyword.lower() in title_lower:
                return False

        # Check any keywords (at least one should be present)
        any_keywords = criteria.get("any_keywords", [])
        if any_keywords:
            found_any = False
            for keyword in any_keywords:
                if keyword.lower() in title_lower:
                    found_any = True
                    break
            if not found_any:
                return False

        return True

    def get_name(self) -> str:
        return "title_keyword"


# Registry of available evaluators
EVALUATOR_REGISTRY = {
    "content_completeness": ContentCompletenessEvaluator(),
    "domain_filter": DomainFilterEvaluator(),
    "article_length": ArticleLengthEvaluator(),
    "date_range": DateRangeEvaluator(),
    "title_keyword": TitleKeywordEvaluator(),
}


def get_evaluator(name: str) -> BooleanEvaluator:
    """Get evaluator by name."""
    if name not in EVALUATOR_REGISTRY:
        available = ", ".join(EVALUATOR_REGISTRY.keys())
        raise ValueError(f"Evaluator '{name}' not found. Available: {available}")
    return EVALUATOR_REGISTRY[name]


def list_evaluators() -> List[Dict[str, str]]:
    """List all available evaluators."""
    return [
        {
            "name": name,
            "description": evaluator.get_description(),
        }
        for name, evaluator in EVALUATOR_REGISTRY.items()
    ] 