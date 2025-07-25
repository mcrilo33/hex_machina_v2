from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Sequence,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from src.hex_machina.storage.base import Base

# Sequences
article_id_seq = Sequence("article_id_seq")
ingestion_op_id_seq = Sequence("ingestion_op_id_seq")
enrichment_id_seq = Sequence("enrichment_id_seq")
workflow_operation_id_seq = Sequence("workflow_operation_id_seq")


class IngestionOperationDB(Base):
    __tablename__ = "ingestion_operations"
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


class WorkflowOperationDB(Base):
    __tablename__ = "workflow_operations"
    id = Column(
        Integer,
        workflow_operation_id_seq,
        server_default=workflow_operation_id_seq.next_value(),
        primary_key=True,
    )
    workflow_name = Column(String(255), nullable=False)
    parameters = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False)
    notes = Column(Text, nullable=True)
    enrichments = relationship("EnrichmentDB", back_populates="workflow_operation")


class ArticleDB(Base):
    __tablename__ = "articles"
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
    article_metadata = Column(Text, nullable=True)
    ingestion_metadata = Column(Text, nullable=True)
    ingestion_run_id = Column(
        Integer, ForeignKey("ingestion_operations.id"), nullable=False
    )
    ingested_at = Column(DateTime, nullable=False)
    ingestion_error_status = Column(String(64), nullable=True)
    ingestion_error_message = Column(Text, nullable=True)
    ingestion_operation = relationship(IngestionOperationDB, back_populates="articles")
    enrichments = relationship(
        "EnrichmentDB", back_populates="article", cascade="all, delete-orphan"
    )


class EnrichmentDB(Base):
    __tablename__ = "enrichments"
    id = Column(
        Integer,
        enrichment_id_seq,
        server_default=enrichment_id_seq.next_value(),
        primary_key=True,
    )
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    workflow_operation_id = Column(
        Integer, ForeignKey("workflow_operations.id"), nullable=False
    )
    enrichment_type = Column(String(64), nullable=False)
    enrichment_data = Column(JSON, nullable=False)
    source = Column(String(64), nullable=False)
    tool_name = Column(String(128), nullable=True)
    tool_params = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False)
    version = Column(String(32), nullable=True)
    article = relationship(ArticleDB, back_populates="enrichments")
    workflow_operation = relationship(WorkflowOperationDB, back_populates="enrichments")
