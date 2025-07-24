"""Hex Machina v2 - AI-driven newsletter service."""

from src.hex_machina.ingestion import (
    ArticleModel,
    IngestionConfig,
    IngestionRunner,
    generate_html_ingestion_report,
)
from src.hex_machina.utils.date_parser import DateParser

__version__ = "0.1.0"
__author__ = "Mathieu Crilout"
__email__ = "mathieu.crilout@gmail.com"

__all__ = [
    "ArticleModel",
    "IngestionConfig",
    "IngestionRunner",
    "generate_html_ingestion_report",
    "DateParser",
]
