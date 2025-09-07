"""Runnables for LangChain tasks."""

# Import all runnables directly
from .article_fetcher import ArticleFetcher
from .article_processor import ArticleProcessor
from .enrichment_saver import EnrichmentSaver
from .example_runnable import AnotherCustomRunnable, ExampleCustomRunnable
from .mock_keyword_extractor import MockKeywordExtractor
from .mock_summarizer import MockSummarizer
from .registry import RunnableRegistry, runnable_registry
from .text_truncator import TextTruncatorRunnable, TransformChain

# Register all runnables
runnable_registry.register("ArticleFetcher", ArticleFetcher)
runnable_registry.register("ArticleProcessor", ArticleProcessor)
runnable_registry.register("EnrichmentSaver", EnrichmentSaver)
runnable_registry.register("AnotherCustomRunnable", AnotherCustomRunnable)
runnable_registry.register("ExampleCustomRunnable", ExampleCustomRunnable)
runnable_registry.register("MockSummarizer", MockSummarizer)
runnable_registry.register("MockKeywordExtractor", MockKeywordExtractor)
runnable_registry.register("TextTruncatorRunnable", TextTruncatorRunnable)
runnable_registry.register("TransformChain", TransformChain)

__all__ = [
    "ArticleFetcher",
    "ArticleProcessor",
    "EnrichmentSaver",
    "AnotherCustomRunnable",
    "ExampleCustomRunnable",
    "MockSummarizer",
    "MockKeywordExtractor",
    "TextTruncatorRunnable",
    "TransformChain",
    "RunnableRegistry",
    "runnable_registry",
]
