"""Ingestion processing module."""

from .article_parser import *
from .scrapy_pipelines import *

__all__ = [
    "ArticleParser",
    "ArticleStorePipeline",
]
