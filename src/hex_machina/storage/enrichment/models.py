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

enrichment_id_seq = Sequence("enrichment_id_seq")
workflow_operation_id_seq = Sequence("workflow_operation_id_seq")


class WorkflowOperationDB(Base):
    """Represents a single enrichment or workflow run/process (ORM model).
    DB suffix: All ORM classes use DB suffix for consistency.
    """

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


class EnrichmentDB(Base):
    """Represents any enrichment result for an article (LLM, ML, human, etc.).
    DB suffix: All ORM classes use DB suffix for consistency.
    """

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

    article = relationship("ArticleDB", back_populates="enrichments")
    workflow_operation = relationship(
        "WorkflowOperationDB", back_populates="enrichments"
    )
