"""Ingestion module for scraping and processing articles."""

from src.hex_machina.ingestion.article_models import ArticleModel, RSSArticlePreview
from src.hex_machina.ingestion.config_loader import load_ingestion_config
from src.hex_machina.ingestion.config_models import IngestionConfig
from src.hex_machina.ingestion.ingestion_report import (
    IngestionReportGenerator,
    generate_html_ingestion_report,
)
from src.hex_machina.ingestion.ingestion_runner import IngestionRunner
from src.hex_machina.ingestion.scrapy_pipelines import ArticleStorePipeline

__all__ = [
    "ArticleModel",
    "RSSArticlePreview",
    "IngestionConfig",
    "load_ingestion_config",
    "IngestionRunner",
    "ArticleStorePipeline",
    "generate_html_ingestion_report",
    "IngestionReportGenerator",
]
