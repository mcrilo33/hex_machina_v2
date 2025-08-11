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
    enrichments = relationship("EnrichmentDB", back_populates="article")

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


class WorkflowOperationDB(Base):
    """Database model for workflow operations."""

    __tablename__ = "workflow_operations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_name = Column(String(255), nullable=False)
    parameters = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running")
    notes = Column(Text, nullable=True)


class EnrichmentDB(Base):
    """Database model for enrichment results."""

    __tablename__ = "enrichments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    workflow_operation_id = Column(String(255), nullable=True)
    enrichment_type = Column(String(100), nullable=False)
    enrichment_data = Column(JSON, nullable=True)
    source = Column(String(100), nullable=False)
    tool_name = Column(String(100), nullable=False)
    tool_params = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    version = Column(String(20), default="1.0.0")

    # Relationships
    article = relationship("ArticleDB", back_populates="enrichments")


class DatasetDB(Base):
    """Database model for datasets."""

    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    data_type = Column(String(50), default="kv")  # kv, chat
    dataset_metadata = Column(
        JSON, nullable=True
    )  # Renamed from metadata to avoid SQLAlchemy conflict
    langsmith_dataset_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    examples = relationship("DatasetExampleDB", back_populates="dataset")


class DatasetExampleDB(Base):
    """Database model for dataset examples."""

    __tablename__ = "dataset_examples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    inputs = Column(JSON, nullable=False)  # LangSmith format
    outputs = Column(JSON, nullable=True)  # Expected outputs
    example_metadata = Column(
        JSON, nullable=True
    )  # Renamed from metadata to avoid SQLAlchemy conflict
    split = Column(
        String(50), nullable=True
    )  # train, validation, test, custom, or NULL for default split
    langsmith_example_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    dataset = relationship("DatasetDB", back_populates="examples")
    article = relationship("ArticleDB")
