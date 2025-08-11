"""Tests for task runner functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from src.hex_machina.core.base import TaskInput, TaskOutput
from src.hex_machina.enrichment.tasks.runner import TaskRunner
from src.hex_machina.storage.models import ArticleDB


class TestTaskRunner:
    """Test TaskRunner functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.task_runner = TaskRunner()

    @patch("src.hex_machina.enrichment.tasks.runner.task_registry")
    @patch("src.hex_machina.enrichment.tasks.runner.get_langsmith_tracer")
    @patch("src.hex_machina.enrichment.tasks.runner.task_config_manager")
    async def test_run_task_success(self, mock_config_manager, mock_tracer, mock_registry):
        """Test successful task execution."""
        # Setup mocks
        mock_task = Mock()
        mock_task.initialize = Mock()
        mock_registry.create_task.return_value = mock_task

        mock_config = {"test": "config"}
        mock_config_manager.load_config.return_value = mock_config
        mock_config_manager.create_langchain_config.return_value = mock_config

        mock_result = TaskOutput(
            task_id="test_task_12345678",
            output_data={"result": "success"},
            metadata={},
            execution_time=1.0,
            created_at="2024-01-01T12:00:00",
        )
        mock_tracer_instance = Mock()
        mock_tracer_instance.execute_task_with_tracing = AsyncMock(return_value=mock_result)
        mock_tracer.return_value = mock_tracer_instance

        # Mock save methods
        self.task_runner._save_results = AsyncMock()

        # Test data
        input_data = {"title": "Test Article", "content": "Test content"}

        # Execute
        result = await self.task_runner.run_task("test_task", input_data)

        # Assertions
        assert result == mock_result
        mock_registry.create_task.assert_called_once_with("test_task", config=mock_config)
        mock_task.initialize.assert_called_once()
        mock_tracer_instance.execute_task_with_tracing.assert_called_once()
        self.task_runner._save_results.assert_called_once()

    @patch("src.hex_machina.enrichment.tasks.runner.task_registry")
    async def test_run_task_creation_failure(self, mock_registry):
        """Test task execution when task creation fails."""
        # Setup mocks
        mock_registry.create_task.return_value = None

        # Test data
        input_data = {"title": "Test Article", "content": "Test content"}

        # Execute and assert
        with pytest.raises(Exception, match="Failed to create task"):
            await self.task_runner.run_task("nonexistent_task", input_data)

    @patch("src.hex_machina.enrichment.tasks.runner.asyncio.gather")
    async def test_run_task_on_articles_success(self, mock_gather):
        """Test running task on multiple articles."""
        # Setup mocks
        mock_articles = [
            ArticleDB(id=1, title="Article 1", text_content="Content 1", url="http://test1.com", url_domain="test1.com"),
            ArticleDB(id=2, title="Article 2", text_content="Content 2", url="http://test2.com", url_domain="test2.com"),
        ]

        mock_results = [
            TaskOutput(
                task_id="test1",
                output_data={"result": "success"},
                metadata={},
                execution_time=1.0,
                created_at="2024-01-01T12:00:00",
            ),
            TaskOutput(
                task_id="test2",
                output_data={"result": "success"},
                metadata={},
                execution_time=1.2,
                created_at="2024-01-01T12:01:00",
            ),
        ]

        mock_gather.return_value = mock_results
        self.task_runner.run_task = AsyncMock(side_effect=mock_results)

        # Execute
        results = await self.task_runner.run_task_on_articles(
            "test_task", mock_articles, batch_size=10
        )

        # Assertions
        assert len(results) == 2
        assert all(isinstance(r, TaskOutput) for r in results)

    async def test_run_task_on_articles_with_skip_existing(self):
        """Test running task on articles with skip_existing flag."""
        # Setup mocks
        mock_articles = [
            ArticleDB(id=1, title="Article 1", text_content="Content 1", url="http://test1.com", url_domain="test1.com"),
            ArticleDB(id=2, title="Article 2", text_content="Content 2", url="http://test2.com", url_domain="test2.com"),
        ]

        # Mock that article 1 is already processed
        self.task_runner._is_article_processed = Mock(side_effect=lambda task, id: id == 1)
        self.task_runner.run_task = AsyncMock(return_value=TaskOutput(
            task_id="test",
            output_data={},
            metadata={},
            execution_time=1.0,
            created_at="2024-01-01T12:00:00",
        ))

        # Execute
        results = await self.task_runner.run_task_on_articles(
            "test_task", mock_articles, skip_existing=True
        )

        # Assertions - only one task should be called (for article 2)
        assert self.task_runner.run_task.call_count == 1

    @patch("src.hex_machina.enrichment.tasks.runner.asyncio.gather")
    async def test_run_task_on_articles_with_exceptions(self, mock_gather):
        """Test running task on articles when some tasks raise exceptions."""
        # Setup mocks
        mock_articles = [
            ArticleDB(id=1, title="Article 1", text_content="Content 1", url="http://test1.com", url_domain="test1.com"),
            ArticleDB(id=2, title="Article 2", text_content="Content 2", url="http://test2.com", url_domain="test2.com"),
        ]

        mock_result = TaskOutput(
            task_id="test1",
            output_data={"result": "success"},
            metadata={},
            execution_time=1.0,
            created_at="2024-01-01T12:00:00",
        )
        mock_exception = Exception("Test error")

        mock_gather.return_value = [mock_result, mock_exception]
        self.task_runner.run_task = AsyncMock()

        # Execute
        results = await self.task_runner.run_task_on_articles(
            "test_task", mock_articles
        )

        # Assertions - only successful result should be returned
        assert len(results) == 1
        assert results[0] == mock_result

    async def test_run_task_on_source_single_article(self):
        """Test running task on single article source."""
        # Mock article resolution
        mock_article = ArticleDB(
            id=1, title="Test Article", text_content="Content", 
            url="http://test.com", url_domain="test.com"
        )
        self.task_runner._resolve_articles_from_source = Mock(return_value=[mock_article])
        self.task_runner.run_task_on_articles = AsyncMock(return_value=[])

        # Execute
        results = await self.task_runner.run_task_on_source(
            "test_task", "single_article", 1
        )

        # Assertions
        self.task_runner._resolve_articles_from_source.assert_called_once_with(
            "single_article", 1, None
        )
        self.task_runner.run_task_on_articles.assert_called_once()

    async def test_run_task_on_source_no_articles(self):
        """Test running task on source when no articles are found."""
        # Mock empty article resolution
        self.task_runner._resolve_articles_from_source = Mock(return_value=[])

        # Execute
        results = await self.task_runner.run_task_on_source(
            "test_task", "invalid_source", "invalid_value"
        )

        # Assertions
        assert results == []

    def test_resolve_articles_from_source_single_article(self):
        """Test resolving single article from source."""
        mock_article = ArticleDB(id=1, title="Test", text_content="Content", url="http://test.com", url_domain="test.com")
        self.task_runner._article_source.resolve_single_article = Mock(return_value=mock_article)

        results = self.task_runner._resolve_articles_from_source("single_article", 1)

        assert results == [mock_article]

    def test_resolve_articles_from_source_single_article_not_found(self):
        """Test resolving single article when not found."""
        self.task_runner._article_source.resolve_single_article = Mock(return_value=None)

        results = self.task_runner._resolve_articles_from_source("single_article", 999)

        assert results == []

    def test_resolve_articles_from_source_multiple_articles(self):
        """Test resolving multiple articles from source."""
        mock_articles = [
            ArticleDB(id=1, title="Test 1", text_content="Content 1", url="http://test1.com", url_domain="test1.com"),
            ArticleDB(id=2, title="Test 2", text_content="Content 2", url="http://test2.com", url_domain="test2.com"),
        ]
        self.task_runner._article_source.resolve_multiple_articles = Mock(return_value=mock_articles)

        results = self.task_runner._resolve_articles_from_source("multiple_articles", [1, 2])

        assert results == mock_articles

    def test_resolve_articles_from_source_with_limit(self):
        """Test resolving articles with limit applied."""
        mock_articles = [ArticleDB(id=i, title=f"Test {i}", text_content=f"Content {i}", 
                                  url=f"http://test{i}.com", url_domain=f"test{i}.com") for i in range(1, 6)]
        self.task_runner._article_source.resolve_all_articles = Mock(return_value=mock_articles)

        results = self.task_runner._resolve_articles_from_source("all_articles", None, limit=3)

        assert len(results) == 3

    def test_resolve_articles_from_source_unknown_type(self):
        """Test resolving articles with unknown source type."""
        results = self.task_runner._resolve_articles_from_source("unknown_type", "value")

        assert results == []

    def test_article_to_input_data(self):
        """Test converting ArticleDB to input data format."""
        article = ArticleDB(
            id=1,
            title="Test Article",
            url="http://test.com",
            url_domain="test.com",
            text_content="Test content"
        )

        input_data = self.task_runner._article_to_input_data(article)

        expected = {
            "id": 1,
            "title": "Test Article",
            "url": "http://test.com",
            "domain": "test.com",
            "content": "Test content",
            "url_domain": "test.com",
        }
        assert input_data == expected

    @patch("src.hex_machina.enrichment.tasks.runner.database_config_manager")
    def test_should_save_to_db_with_article_context(self, mock_config_manager):
        """Test determining save to DB when article context is detected."""
        mock_config_manager.get_enable_by_default.return_value = True
        self.task_runner._detect_article_context = Mock(return_value={"article_id": 1})

        input_data = {"id": 1, "title": "Test"}
        result = self.task_runner._should_save_to_db(input_data)

        assert result is True

    def test_should_save_to_db_no_article_context(self):
        """Test determining save to DB when no article context is detected."""
        self.task_runner._detect_article_context = Mock(return_value=None)

        input_data = {"title": "Test"}
        result = self.task_runner._should_save_to_db(input_data)

        assert result is False

    @patch("src.hex_machina.enrichment.tasks.runner.get_storage_manager")
    def test_is_article_processed_true(self, mock_get_storage_manager):
        """Test checking if article is processed when it is."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = Mock()
        mock_storage_manager = Mock()
        mock_storage_manager.session.return_value.__enter__.return_value = mock_session
        mock_get_storage_manager.return_value = mock_storage_manager

        result = self.task_runner._is_article_processed("test_task", 1)

        assert result is True

    @patch("src.hex_machina.enrichment.tasks.runner.get_storage_manager")
    def test_is_article_processed_false(self, mock_get_storage_manager):
        """Test checking if article is processed when it is not."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_storage_manager = Mock()
        mock_storage_manager.session.return_value.__enter__.return_value = mock_session
        mock_get_storage_manager.return_value = mock_storage_manager

        result = self.task_runner._is_article_processed("test_task", 1)

        assert result is False

    @patch("src.hex_machina.enrichment.tasks.runner.get_storage_manager")
    def test_is_article_processed_exception(self, mock_get_storage_manager):
        """Test checking if article is processed when exception occurs."""
        mock_get_storage_manager.side_effect = Exception("Database error")

        result = self.task_runner._is_article_processed("test_task", 1)

        assert result is False

    async def test_save_results_success(self):
        """Test successful saving of results."""
        # Setup mocks
        self.task_runner._task_storage.save_task_input = AsyncMock()
        self.task_runner._task_storage.save_task_output = AsyncMock()
        self.task_runner._database_storage.save_task_output = AsyncMock()

        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={"test": "data"},
            save_to_db=True
        )
        task_output = TaskOutput(
            task_id="test",
            output_data={"result": "success"},
            metadata={},
            execution_time=1.0,
            created_at="2024-01-01T12:00:00",
        )

        # Execute
        await self.task_runner._save_results(task_input, task_output)

        # Assertions
        self.task_runner._task_storage.save_task_input.assert_called_once_with(task_input)
        self.task_runner._task_storage.save_task_output.assert_called_once_with(task_output)
        self.task_runner._database_storage.save_task_output.assert_called_once_with(task_output)

    async def test_save_results_no_db_save(self):
        """Test saving results when DB save is disabled."""
        # Setup mocks
        self.task_runner._task_storage.save_task_input = AsyncMock()
        self.task_runner._task_storage.save_task_output = AsyncMock()
        self.task_runner._database_storage.save_task_output = AsyncMock()

        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={"test": "data"},
            save_to_db=False
        )
        task_output = TaskOutput(
            task_id="test",
            output_data={"result": "success"},
            metadata={},
            execution_time=1.0,
            created_at="2024-01-01T12:00:00",
        )

        # Execute
        await self.task_runner._save_results(task_input, task_output)

        # Assertions
        self.task_runner._task_storage.save_task_input.assert_called_once_with(task_input)
        self.task_runner._task_storage.save_task_output.assert_called_once_with(task_output)
        self.task_runner._database_storage.save_task_output.assert_not_called()

    async def test_save_results_with_error(self):
        """Test saving results when task has error."""
        # Setup mocks
        self.task_runner._task_storage.save_task_input = AsyncMock()
        self.task_runner._task_storage.save_task_output = AsyncMock()
        self.task_runner._database_storage.save_task_output = AsyncMock()

        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={"test": "data"},
            save_to_db=True
        )
        task_output = TaskOutput(
            task_id="test",
            output_data={},
            metadata={},
            execution_time=1.0,
            error="Test error",
            created_at="2024-01-01T12:00:00",
        )

        # Execute
        await self.task_runner._save_results(task_input, task_output)

        # Assertions
        self.task_runner._task_storage.save_task_input.assert_called_once_with(task_input)
        self.task_runner._task_storage.save_task_output.assert_called_once_with(task_output)
        self.task_runner._database_storage.save_task_output.assert_not_called()  # No DB save on error

    def test_detect_article_context_by_id(self):
        """Test detecting article context by ID."""
        mock_article = ArticleDB(id=1, title="Test", text_content="Content", url="http://test.com", url_domain="test.com")
        self.task_runner._find_article_by_id = Mock(return_value=mock_article)

        input_data = {"id": 1}
        context = self.task_runner._detect_article_context(input_data)

        assert context == {"article_id": 1, "source": "database"}

    def test_detect_article_context_by_url(self):
        """Test detecting article context by URL."""
        mock_article = ArticleDB(id=1, title="Test", text_content="Content", url="http://test.com", url_domain="test.com")
        self.task_runner._find_article_by_id = Mock(return_value=None)
        self.task_runner._find_article_by_url = Mock(return_value=mock_article)

        input_data = {"url": "http://test.com"}
        context = self.task_runner._detect_article_context(input_data)

        assert context == {"article_id": 1, "source": "database"}

    def test_detect_article_context_by_title_domain(self):
        """Test detecting article context by title and domain."""
        mock_article = ArticleDB(id=1, title="Test", text_content="Content", url="http://test.com", url_domain="test.com")
        self.task_runner._find_article_by_id = Mock(return_value=None)
        self.task_runner._find_article_by_url = Mock(return_value=None)
        self.task_runner._find_article_by_title_domain = Mock(return_value=mock_article)

        input_data = {"title": "Test", "domain": "test.com"}
        context = self.task_runner._detect_article_context(input_data)

        assert context == {"article_id": 1, "source": "database"}

    def test_detect_article_context_by_title_url_domain(self):
        """Test detecting article context by title and url_domain."""
        mock_article = ArticleDB(id=1, title="Test", text_content="Content", url="http://test.com", url_domain="test.com")
        self.task_runner._find_article_by_id = Mock(return_value=None)
        self.task_runner._find_article_by_url = Mock(return_value=None)
        self.task_runner._find_article_by_title_domain = Mock(side_effect=[None, mock_article])

        input_data = {"title": "Test", "url_domain": "test.com"}
        context = self.task_runner._detect_article_context(input_data)

        assert context == {"article_id": 1, "source": "database"}

    def test_detect_article_context_not_found(self):
        """Test detecting article context when no article is found."""
        self.task_runner._find_article_by_id = Mock(return_value=None)
        self.task_runner._find_article_by_url = Mock(return_value=None)
        self.task_runner._find_article_by_title_domain = Mock(return_value=None)

        input_data = {"title": "Nonexistent"}
        context = self.task_runner._detect_article_context(input_data)

        assert context is None

    @patch("src.hex_machina.enrichment.tasks.runner.get_storage_manager")
    @patch("src.hex_machina.enrichment.tasks.runner.database_config_manager")
    def test_find_article_by_id_success(self, mock_config_manager, mock_get_storage_manager):
        """Test finding article by ID successfully."""
        mock_config_manager.get_db_path.return_value = "test.db"
        
        mock_article = ArticleDB(id=1, title="Test", text_content="Content", url="http://test.com", url_domain="test.com")
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_article
        mock_storage_manager = Mock()
        mock_storage_manager.session.return_value.__enter__.return_value = mock_session
        mock_get_storage_manager.return_value = mock_storage_manager

        result = self.task_runner._find_article_by_id(1)

        assert result == mock_article

    @patch("src.hex_machina.enrichment.tasks.runner.get_storage_manager")
    @patch("src.hex_machina.enrichment.tasks.runner.database_config_manager")
    def test_find_article_by_id_not_found(self, mock_config_manager, mock_get_storage_manager):
        """Test finding article by ID when not found."""
        mock_config_manager.get_db_path.return_value = "test.db"
        
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_storage_manager = Mock()
        mock_storage_manager.session.return_value.__enter__.return_value = mock_session
        mock_get_storage_manager.return_value = mock_storage_manager

        result = self.task_runner._find_article_by_id(999)

        assert result is None

    @patch("src.hex_machina.enrichment.tasks.runner.get_storage_manager")
    @patch("src.hex_machina.enrichment.tasks.runner.database_config_manager")
    def test_find_article_by_id_exception(self, mock_config_manager, mock_get_storage_manager):
        """Test finding article by ID when exception occurs."""
        mock_config_manager.get_db_path.return_value = "test.db"
        mock_get_storage_manager.side_effect = Exception("Database error")

        result = self.task_runner._find_article_by_id(1)

        assert result is None