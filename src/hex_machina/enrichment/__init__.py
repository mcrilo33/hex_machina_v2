"""Enrichment module for Hex Machina v2.

This module provides content enrichment capabilities through LLM tasks,
workflows, and evaluation systems.
"""

from .core import (
    EnrichmentConfig,
    EnrichmentEvaluator,
    EnrichmentTask,
    EnrichmentWorkflow,
    TaskRegistry,
)
from .core.registry import task_registry
from .models import (
    ArticleInput,
    CompletenessOutput,
    EvaluationMetrics,
)
from .storage import (
    EnrichmentStorage,
    LangSmithStorage,
    LocalStorage,
)

# Import and register tasks
from .tasks.content_completeness_langchain import ContentCompletenessLangChainTask

# Register tasks
task_registry.register(ContentCompletenessLangChainTask)

__all__ = [
    # Core components
    "EnrichmentTask",
    "EnrichmentWorkflow",
    "EnrichmentEvaluator",
    "TaskRegistry",
    "EnrichmentConfig",
    # Data models
    "ArticleInput",
    "CompletenessOutput",
    "EvaluationMetrics",
    # Storage
    "EnrichmentStorage",
    "LocalStorage",
    "LangSmithStorage",
    # Tasks
    "ContentCompletenessLangChainTask",
]
