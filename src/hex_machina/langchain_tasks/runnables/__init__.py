"""Custom runnables for LangChain tasks."""

from .article_fetcher import ArticleFetcher
from .article_processor import ArticleProcessor
from .enrichment_saver import EnrichmentSaver
from .mock_keyword_extractor import MockKeywordExtractor
from .mock_summarizer import MockSummarizer
from .registry import RunnableRegistry, runnable_registry

# Register our custom runnables
runnable_registry.register("ArticleFetcher", ArticleFetcher)
runnable_registry.register("ArticleProcessor", ArticleProcessor)
runnable_registry.register("EnrichmentSaver", EnrichmentSaver)
runnable_registry.register("MockSummarizer", MockSummarizer)
runnable_registry.register("MockKeywordExtractor", MockKeywordExtractor)

__all__ = [
    "ArticleFetcher",
    "ArticleProcessor",
    "EnrichmentSaver",
    "MockSummarizer",
    "MockKeywordExtractor",
    "RunnableRegistry",
    "runnable_registry",
]
