"""Integration tests for task execution workflows."""

import asyncio
import json
import tempfile
import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.hex_machina.core.base import TaskInput, TaskOutput
from src.hex_machina.enrichment.tasks.runner import TaskRunner
from src.hex_machina.enrichment.tasks.registry import TaskRegistry
from src.hex_machina.enrichment.core.article_source import ArticleSource
from src.hex_machina.storage.models import ArticleDB


@pytest.mark.asyncio
class TestTaskIntegration:
    """Integration tests for task execution workflows."""

    def setup_method(self):
        """Setup test environment."""
        self.task_runner = TaskRunner()

    @patch("src.hex_machina.enrichment.tasks.runner.task_registry")
    @patch("src.hex_machina.enrichment.tasks.runner.get_langsmith_tracer")
    @patch("src.hex_machina.enrichment.tasks.runner.task_config_manager")
    async def test_end_to_end_task_execution(self, mock_config_manager, mock_tracer, mock_registry):
        """Test complete end-to-end task execution."""
        # Setup mocks for task creation and execution
        mock_task = Mock()
        mock_task.initialize = Mock()
        mock_registry.create_task.return_value = mock_task

        mock_config = {
            "llm_provider": "openrouter",
            "llm_model": "test-model",
            "prompt_template": "Test template",
        }
        mock_config_manager.load_config.return_value = mock_config
        mock_config_manager.create_langchain_config.return_value = mock_config

        # Mock successful task execution
        mock_result = TaskOutput(
            task_id="test_task_12345678",
            output_data={"completeness_score": 0.85, "analysis": "Content is well structured"},
            metadata={"task_name": "content_completeness"},
            execution_time=2.5,
            created_at="2024-01-01T12:00:00",
        )
        
        mock_tracer_instance = Mock()
        mock_tracer_instance.execute_task_with_tracing = AsyncMock(return_value=mock_result)
        mock_tracer.return_value = mock_tracer_instance

        # Mock save methods
        self.task_runner._save_results = AsyncMock()

        # Execute task
        input_data = {
            "title": "Test Article",
            "content": "This is a comprehensive test article with detailed information.",
            "url": "http://example.com/article",
        }

        result = await self.task_runner.run_task("content_completeness", input_data)

        # Verify execution flow
        assert result == mock_result
        mock_registry.create_task.assert_called_once()
        mock_task.initialize.assert_called_once()
        mock_tracer_instance.execute_task_with_tracing.assert_called_once()
        self.task_runner._save_results.assert_called_once()

    @patch("src.hex_machina.enrichment.tasks.runner.asyncio.gather")
    async def test_batch_processing_workflow(self, mock_gather):
        """Test batch processing of multiple articles."""
        # Create test articles
        articles = [
            ArticleDB(
                id=1,
                title="Article 1",
                text_content="Content for article 1",
                url="http://example.com/1",
                url_domain="example.com"
            ),
            ArticleDB(
                id=2,
                title="Article 2", 
                text_content="Content for article 2",
                url="http://example.com/2",
                url_domain="example.com"
            ),
            ArticleDB(
                id=3,
                title="Article 3",
                text_content="Content for article 3",
                url="http://example.com/3",
                url_domain="example.com"
            ),
        ]

        # Mock successful results for all articles
        mock_results = [
            TaskOutput(
                task_id=f"test_{i}",
                output_data={"completeness_score": 0.8 + (i * 0.05)},
                metadata={"task_name": "test_task"},
                execution_time=1.0 + i,
                created_at="2024-01-01T12:00:00",
            )
            for i in range(3)
        ]

        mock_gather.return_value = mock_results
        self.task_runner.run_task = AsyncMock(side_effect=mock_results)

        # Execute batch processing
        results = await self.task_runner.run_task_on_articles(
            "test_task", articles, batch_size=2, max_concurrent=2
        )

        # Verify results
        assert len(results) == 3
        assert all(isinstance(r, TaskOutput) for r in results)
        assert results[0].output_data["completeness_score"] == 0.8
        assert results[2].output_data["completeness_score"] == 0.9

    async def test_error_handling_in_batch_processing(self):
        """Test error handling during batch processing."""
        # Create test articles
        articles = [
            ArticleDB(
                id=1,
                title="Good Article",
                text_content="Valid content",
                url="http://example.com/1",
                url_domain="example.com"
            ),
            ArticleDB(
                id=2,
                title="Bad Article",
                text_content="",  # Empty content should cause validation error
                url="http://example.com/2",
                url_domain="example.com"
            ),
        ]

        # Mock mixed results - one success, one failure
        success_result = TaskOutput(
            task_id="test_1",
            output_data={"completeness_score": 0.85},
            metadata={"task_name": "test_task"},
            execution_time=1.5,
            created_at="2024-01-01T12:00:00",
        )
        
        error_result = TaskOutput(
            task_id="test_2",
            output_data={},
            metadata={"task_name": "test_task"},
            execution_time=0.5,
            error="Validation failed: empty content",
            created_at="2024-01-01T12:00:00",
        )

        # Mock the run_task method to return different results
        self.task_runner.run_task = AsyncMock(side_effect=[success_result, error_result])

        with patch("src.hex_machina.enrichment.tasks.runner.asyncio.gather") as mock_gather:
            mock_gather.return_value = [success_result, error_result]

            results = await self.task_runner.run_task_on_articles("test_task", articles)

        # Should return both results, including the error
        assert len(results) == 2
        assert results[0].error is None
        assert results[1].error is not None

    async def test_article_source_resolution_workflow(self):
        """Test complete article source resolution workflow."""
        # Mock article source resolution
        mock_articles = [
            ArticleDB(
                id=1,
                title="Resolved Article",
                text_content="Resolved content",
                url="http://example.com/resolved",
                url_domain="example.com"
            ),
        ]

        self.task_runner._resolve_articles_from_source = Mock(return_value=mock_articles)
        self.task_runner.run_task_on_articles = AsyncMock(return_value=[
            TaskOutput(
                task_id="resolved_task",
                output_data={"status": "completed"},
                metadata={"task_name": "test_task"},
                execution_time=1.0,
                created_at="2024-01-01T12:00:00",
            )
        ])

        # Test different source types
        source_types = [
            ("single_article", 1),
            ("multiple_articles", [1, 2, 3]),
            ("ingestion_operation", 123),
            ("dataset", "test_dataset"),
            ("all_articles", None),
        ]

        for source_type, source_value in source_types:
            results = await self.task_runner.run_task_on_source(
                "test_task", source_type, source_value
            )

            assert len(results) == 1
            assert results[0].output_data["status"] == "completed"
            
            # Verify source resolution was called correctly
            self.task_runner._resolve_articles_from_source.assert_called_with(
                source_type, source_value, None
            )

    async def test_skip_existing_functionality(self):
        """Test skip existing articles functionality."""
        # Create test articles
        articles = [
            ArticleDB(id=1, title="New Article", text_content="Content", url="http://example.com/1", url_domain="example.com"),
            ArticleDB(id=2, title="Processed Article", text_content="Content", url="http://example.com/2", url_domain="example.com"),
            ArticleDB(id=3, title="Another New Article", text_content="Content", url="http://example.com/3", url_domain="example.com"),
        ]

        # Mock that article 2 is already processed
        self.task_runner._is_article_processed = Mock(side_effect=lambda task, id: id == 2)
        
        # Mock task execution
        self.task_runner.run_task = AsyncMock(return_value=TaskOutput(
            task_id="test",
            output_data={"status": "completed"},
            metadata={},
            execution_time=1.0,
            created_at="2024-01-01T12:00:00",
        ))

        with patch("src.hex_machina.enrichment.tasks.runner.asyncio.gather") as mock_gather:
            mock_gather.return_value = [
                TaskOutput(task_id="test_1", output_data={}, metadata={}, execution_time=1.0, created_at="2024-01-01T12:00:00"),
                TaskOutput(task_id="test_3", output_data={}, metadata={}, execution_time=1.0, created_at="2024-01-01T12:00:00"),
            ]

            results = await self.task_runner.run_task_on_articles(
                "test_task", articles, skip_existing=True
            )

        # Should only process articles 1 and 3 (skip article 2)
        assert self.task_runner.run_task.call_count == 2
        assert len(results) == 2

    async def test_database_save_workflow(self):
        """Test database save workflow."""
        # Mock article detection and save operations
        self.task_runner._detect_article_context = Mock(return_value={"article_id": 1, "source": "database"})
        self.task_runner._task_storage.save_task_input = AsyncMock()
        self.task_runner._task_storage.save_task_output = AsyncMock()
        self.task_runner._database_storage.save_task_output = AsyncMock()

        with patch("src.hex_machina.enrichment.tasks.runner.database_config_manager") as mock_config:
            mock_config.get_enable_by_default.return_value = True

            task_input = TaskInput(
                task_id="test",
                task_name="test_task",
                input_data={"id": 1, "title": "Test Article", "content": "Test content"},
                save_to_db=True
            )

            task_output = TaskOutput(
                task_id="test",
                output_data={"result": "success"},
                metadata={},
                execution_time=1.0,
                created_at="2024-01-01T12:00:00",
            )

            await self.task_runner._save_results(task_input, task_output)

            # Verify all save operations were called
            self.task_runner._task_storage.save_task_input.assert_called_once_with(task_input)
            self.task_runner._task_storage.save_task_output.assert_called_once_with(task_output)
            self.task_runner._database_storage.save_task_output.assert_called_once_with(task_output)

    def test_article_context_detection_workflow(self):
        """Test article context detection workflow."""
        # Test various input formats for context detection
        test_cases = [
            ({"id": 1}, "ID lookup"),
            ({"url": "http://example.com/article"}, "URL lookup"),
            ({"title": "Test Article", "domain": "example.com"}, "Title/domain lookup"),
            ({"title": "Test Article", "url_domain": "example.com"}, "Title/url_domain lookup"),
        ]

        for input_data, description in test_cases:
            # Mock article found
            mock_article = ArticleDB(
                id=1,
                title="Test Article",
                text_content="Content",
                url="http://example.com/article",
                url_domain="example.com"
            )

            if "id" in input_data:
                self.task_runner._find_article_by_id = Mock(return_value=mock_article)
                self.task_runner._find_article_by_url = Mock(return_value=None)
                self.task_runner._find_article_by_title_domain = Mock(return_value=None)
            elif "url" in input_data:
                self.task_runner._find_article_by_id = Mock(return_value=None)
                self.task_runner._find_article_by_url = Mock(return_value=mock_article)
                self.task_runner._find_article_by_title_domain = Mock(return_value=None)
            else:
                self.task_runner._find_article_by_id = Mock(return_value=None)
                self.task_runner._find_article_by_url = Mock(return_value=None)
                self.task_runner._find_article_by_title_domain = Mock(return_value=mock_article)

            context = self.task_runner._detect_article_context(input_data)
            
            assert context is not None, f"Failed for {description}"
            assert context["article_id"] == 1, f"Wrong article ID for {description}"
            assert context["source"] == "database", f"Wrong source for {description}"

    async def test_concurrent_task_execution(self):
        """Test concurrent execution of multiple tasks."""
        # Create multiple tasks to run concurrently
        task_data = [
            {"title": f"Article {i}", "content": f"Content {i}"} 
            for i in range(5)
        ]

        # Mock task execution
        async def mock_run_task(task_name, input_data):
            # Simulate some processing time
            await asyncio.sleep(0.1)
            return TaskOutput(
                task_id=f"task_{input_data['title']}",
                output_data={"processed": True},
                metadata={"task_name": task_name},
                execution_time=0.1,
                created_at="2024-01-01T12:00:00",
            )

        self.task_runner.run_task = mock_run_task

        # Execute tasks concurrently
        tasks = [
            self.task_runner.run_task("test_task", data) 
            for data in task_data
        ]
        
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()

        # Verify results
        assert len(results) == 5
        assert all(r.output_data["processed"] for r in results)
        
        # Should complete in roughly 0.1s (concurrent) rather than 0.5s (sequential)
        execution_time = end_time - start_time
        assert execution_time < 0.3, f"Execution took too long: {execution_time}s"

    async def test_input_file_processing_workflow(self):
        """Test input file processing workflow."""
        # Create test input file
        test_data = {
            "title": "File-based Article",
            "content": "Content loaded from file",
            "metadata": {"source": "file"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_file_path = f.name

        try:
            # Test file resolution
            article_source = ArticleSource()
            with patch.object(article_source, '__init__', return_value=None):
                result = article_source.resolve_input_file(temp_file_path)
                assert result == test_data

        finally:
            import os
            os.unlink(temp_file_path)

    def test_task_registry_integration(self):
        """Test task registry integration."""
        registry = TaskRegistry()
        
        # Verify built-in tasks are registered
        tasks = registry.list_tasks()
        assert "ContentCompletenessLangChainTask" in tasks
        
        # Test task creation
        config = {
            "llm_provider": "openrouter",
            "llm_model": "test-model",
            "prompt_template": "Test template",
        }
        
        task = registry.create_task("ContentCompletenessLangChainTask", config)
        assert task is not None
        assert task.name == "content_completeness_langchain"
        
        # Test task info
        task_info = registry.get_task_info("ContentCompletenessLangChainTask")
        assert task_info is not None
        assert task_info["is_langchain"] is True