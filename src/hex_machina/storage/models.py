from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ArticleDB(Base):
    """Database model for articles."""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)
    source_url = Column(String(1000), nullable=True)
    url_domain = Column(String(255), nullable=True)
    published_date = Column(DateTime, nullable=True)
    html_content = Column(Text, nullable=True)
    text_content = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    article_metadata = Column(JSON, nullable=True)
    ingestion_metadata = Column(JSON, nullable=True)
    ingestion_run_id = Column(Integer, ForeignKey("ingestion_operations.id"))
    ingested_at = Column(DateTime, default=datetime.now)
    ingestion_error_status = Column(String(50), nullable=True)
    ingestion_error_message = Column(Text, nullable=True)

    # Relationships
    ingestion_operation = relationship(
        "IngestionOperationDB", back_populates="articles"
    )

    # Unique constraint on url_domain and title
    __table_args__ = (
        UniqueConstraint("url_domain", "title", name="unique_article_domain_title"),
    )


class IngestionOperationDB(Base):
    """Database model for ingestion operations."""

    __tablename__ = "ingestion_operations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    num_articles_processed = Column(Integer, default=0)
    num_errors = Column(Integer, default=0)
    status = Column(String(50), default="running")
    parameters = Column(JSON, nullable=True)

    # Relationships
    articles = relationship("ArticleDB", back_populates="ingestion_operation")


class EnrichmentDB(Base):
    """Simplified enrichment model - only essential fields."""

    __tablename__ = "enrichments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, nullable=False)  # Generic foreign key, no relationship
    enrichment_type = Column(String(100), nullable=False)
    content = Column(JSON, nullable=False)  # The actual enrichment data
    enrichment_metadata = Column(JSON, nullable=True)  # Auto-generated metadata as JSON
    created_at = Column(DateTime, default=datetime.now)

    # No relationships - completely decoupled
