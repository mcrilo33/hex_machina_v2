"""Pytest configuration and fixtures for enrichment tasks tests."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from src.hex_machina.enrichment.tasks.base.langchain_task import LangChainTaskConfig
from src.hex_machina.storage.models import ArticleDB


@pytest.fixture
def mock_langchain_config():
    """Fixture providing a mock LangChain task configuration."""
    return LangChainTaskConfig(
        llm_provider="openrouter",
        llm_model="anthropic/claude-3-haiku",
        prompt_template="Test template: {content}",
        temperature=0.0,
        max_tokens=1000,
        timeout=30,
    )


@pytest.fixture
def sample_articles():
    """Fixture providing sample ArticleDB objects for testing."""
    return [
        ArticleDB(
            id=1,
            title="Sample Article 1",
            text_content="This is the content of the first sample article.",
            url="http://example.com/article1",
            url_domain="example.com",
            ingestion_operation_id=1,
        ),
        ArticleDB(
            id=2,
            title="Sample Article 2",
            text_content="This is the content of the second sample article.",
            url="http://example.com/article2",
            url_domain="example.com",
            ingestion_operation_id=1,
        ),
        ArticleDB(
            id=3,
            title="Sample Article 3",
            text_content="This is the content of the third sample article.",
            url="http://test.com/article3",
            url_domain="test.com",
            ingestion_operation_id=2,
        ),
    ]


@pytest.fixture
def mock_task_input():
    """Fixture providing a mock task input with common test data."""
    from src.hex_machina.core.base import TaskInput
    
    return TaskInput(
        task_id="test_task_12345678",
        task_name="test_task",
        input_data={
            "title": "Test Article",
            "content": "This is test content for validation and processing.",
            "url": "http://example.com/test",
            "domain": "example.com",
        },
        save_to_db=False,
    )


@pytest.fixture
def mock_task_output():
    """Fixture providing a mock task output with common test data."""
    from src.hex_machina.core.base import TaskOutput
    
    return TaskOutput(
        task_id="test_task_12345678",
        output_data={
            "completeness_score": 0.85,
            "analysis": "Content is well structured and comprehensive.",
        },
        metadata={
            "task_name": "test_task",
            "llm_provider": "openrouter",
            "llm_model": "test-model",
        },
        execution_time=2.5,
        created_at="2024-01-01T12:00:00",
    )


@pytest.fixture
def temp_json_file():
    """Fixture providing a temporary JSON file for testing file operations."""
    data = {
        "title": "Test Article from File",
        "content": "Content loaded from temporary file.",
        "metadata": {"source": "file", "test": True},
    }
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        import json
        json.dump(data, f)
        temp_file_path = f.name
    
    yield temp_file_path, data
    
    # Cleanup
    os.unlink(temp_file_path)


@pytest.fixture
def mock_storage_manager():
    """Fixture providing a mock storage manager."""
    mock_manager = Mock()
    mock_session = Mock()
    mock_manager.session.return_value.__enter__.return_value = mock_session
    mock_manager.session.return_value.__exit__.return_value = None
    return mock_manager, mock_session


@pytest.fixture
def mock_database_config():
    """Fixture providing mock database configuration."""
    with patch("src.hex_machina.enrichment.core.article_source.DatabaseConfigManager") as mock_config_class:
        mock_config = Mock()
        mock_config.get_db_path.return_value = "test.db"
        mock_config_class.return_value = mock_config
        yield mock_config


@pytest.fixture
def mock_env_config():
    """Fixture providing mock environment configuration."""
    with patch("src.hex_machina.enrichment.config.EnvConfig") as mock_env_class:
        mock_env = Mock()
        mock_env.get_api_key.return_value = "test-api-key"
        mock_env_class.load.return_value = mock_env
        yield mock_env


@pytest.fixture
def mock_langsmith_tracer():
    """Fixture providing mock LangSmith tracer."""
    with patch("src.hex_machina.enrichment.tasks.runner.get_langsmith_tracer") as mock_tracer_func:
        mock_tracer = Mock()
        mock_tracer.execute_task_with_tracing = Mock()
        mock_tracer.trace_llm_call = Mock()
        mock_tracer_func.return_value = mock_tracer
        yield mock_tracer


@pytest.fixture
def mock_task_config_manager():
    """Fixture providing mock task configuration manager."""
    with patch("src.hex_machina.enrichment.tasks.runner.task_config_manager") as mock_manager:
        mock_manager.load_config.return_value = {
            "llm_provider": "openrouter",
            "llm_model": "test-model",
            "prompt_template": "Test template",
        }
        mock_manager.create_langchain_config.return_value = {
            "llm_provider": "openrouter",
            "llm_model": "test-model",
            "prompt_template": "Test template",
        }
        yield mock_manager


@pytest.fixture
def mock_task_registry():
    """Fixture providing mock task registry."""
    with patch("src.hex_machina.enrichment.tasks.runner.task_registry") as mock_registry:
        mock_task = Mock()
        mock_task.initialize = Mock()
        mock_registry.create_task.return_value = mock_task
        mock_registry.list_tasks.return_value = ["TestTask", "ContentCompletenessLangChainTask"]
        yield mock_registry, mock_task


@pytest.fixture(autouse=True)
def disable_logging():
    """Fixture to disable logging during tests to reduce noise."""
    import logging
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture
def mock_llm_chain():
    """Fixture providing a mock LangChain LLM chain."""
    from unittest.mock import AsyncMock
    
    mock_chain = Mock()
    mock_chain.ainvoke = AsyncMock(return_value={
        "completeness_score": 0.85,
        "analysis": "Content appears comprehensive",
    })
    mock_chain.with_config = Mock(return_value=mock_chain)
    return mock_chain


@pytest.fixture
def mock_prompt_template():
    """Fixture providing a mock LangChain prompt template."""
    mock_template = Mock()
    mock_template.__or__ = Mock()  # For chaining with |
    return mock_template


@pytest.fixture
def mock_output_parser():
    """Fixture providing a mock LangChain output parser."""
    mock_parser = Mock()
    mock_parser.parse = Mock(return_value={
        "completeness_score": 0.85,
        "analysis": "Parsed analysis",
    })
    return mock_parser


# Helper functions for test utilities
def create_test_article(article_id=1, title="Test Article", content="Test content", domain="test.com"):
    """Helper function to create test ArticleDB objects."""
    return ArticleDB(
        id=article_id,
        title=title,
        text_content=content,
        url=f"http://{domain}/article{article_id}",
        url_domain=domain,
    )


def create_test_task_input(task_id="test", task_name="test_task", **input_data):
    """Helper function to create test TaskInput objects."""
    from src.hex_machina.core.base import TaskInput
    
    default_data = {
        "title": "Test Article",
        "content": "Test content",
    }
    default_data.update(input_data)
    
    return TaskInput(
        task_id=task_id,
        task_name=task_name,
        input_data=default_data,
    )


def create_test_task_output(task_id="test", **output_data):
    """Helper function to create test TaskOutput objects."""
    from src.hex_machina.core.base import TaskOutput
    
    default_data = {
        "result": "success",
        "score": 0.85,
    }
    default_data.update(output_data)
    
    return TaskOutput(
        task_id=task_id,
        output_data=default_data,
        metadata={"task_name": "test_task"},
        execution_time=1.0,
        created_at="2024-01-01T12:00:00",
    )