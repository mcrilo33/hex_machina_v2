from sqlalchemy import Column, DateTime, ForeignKey, Integer, Sequence, String, Text
from sqlalchemy.orm import relationship

from src.hex_machina.storage.base import Base


class IngestionOperationDB(Base):
    """Represents a single ingestion run/process (ORM model).

    Attributes:
        id (int): Primary key, unique identifier for the ingestion run.
        start_time (datetime): When the ingestion started.
        end_time (datetime): When the ingestion finished.
        num_articles_processed (int): Number of articles processed in this run.
        num_errors (int): Number of articles that failed in this run.
        status (str): Status of the ingestion run (e.g., 'success', 'partial', 'failed').
        parameters (str): (Optional) Parameters/settings used for this run, stored as a JSON string.
    """

    __tablename__ = "ingestion_operations"

    ingestion_op_id_seq = Sequence("ingestion_op_id_seq")
    id = Column(
        Integer,
        ingestion_op_id_seq,
        server_default=ingestion_op_id_seq.next_value(),
        primary_key=True,
    )
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    num_articles_processed = Column(Integer, nullable=False)
    num_errors = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False)
    parameters = Column(Text, nullable=True)

    articles = relationship("ArticleDB", back_populates="ingestion_operation")


class ArticleDB(Base):
    """Represents an article and its ingestion status.

    Attributes:
        id (int): Primary key, unique article identifier.
        title (str): Article title.
        url (str): URL of the article.
        source_url (str): URL of the RSS feed source.
        url_domain (str): Domain of the article URL.
        published_date (datetime): Publication date.
        html_content (str): Raw HTML content.
        text_content (str): Extracted text content.
        author (str): Article author (optional).
        article_metadata (str): Additional metadata as a JSON string (tags, summary, etc.).
        ingestion_metadata (str): Ingestion-related metadata as a JSON string.
        ingestion_run_id (int): Foreign key to IngestionOperation.
        ingested_at (datetime): Timestamp when the article was ingested.
        ingestion_error_status (str): Error status if ingestion failed (optional).
        ingestion_error_message (str): Error message if ingestion failed (optional).
        enrichments (list[Enrichment]): All enrichment results for this article.
    """

    __tablename__ = "articles"

    article_id_seq = Sequence("article_id_seq")
    id = Column(
        Integer,
        article_id_seq,
        server_default=article_id_seq.next_value(),
        primary_key=True,
    )
    title = Column(String(512), nullable=False)
    url = Column(String(2048), nullable=False)
    source_url = Column(String(2048), nullable=False)
    url_domain = Column(String(255), nullable=False)
    published_date = Column(DateTime, nullable=False)
    html_content = Column(Text, nullable=False)
    text_content = Column(Text, nullable=False)
    author = Column(String(255), nullable=True)
    article_metadata = Column(
        Text, nullable=True
    )  # Store as JSON string for tags, summary, etc.
    ingestion_metadata = Column(
        Text, nullable=True
    )  # Store as JSON string for ingestion-related metadata (e.g., scraper name)
    ingestion_run_id = Column(
        Integer, ForeignKey("ingestion_operations.id"), nullable=False
    )
    ingested_at = Column(DateTime, nullable=False)
    ingestion_error_status = Column(String(64), nullable=True)
    ingestion_error_message = Column(Text, nullable=True)

    ingestion_operation = relationship(
        "IngestionOperationDB", back_populates="articles"
    )

    enrichments = relationship(
        "EnrichmentDB", back_populates="article", cascade="all, delete-orphan"
    )
