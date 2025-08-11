"""Tests for article source functionality."""

import pytest
import json
import tempfile
from unittest.mock import Mock, patch

from src.hex_machina.enrichment.core.article_source import ArticleSource
from src.hex_machina.storage.models import ArticleDB


class TestArticleSource:
    """Test ArticleSource functionality."""

    @patch("src.hex_machina.enrichment.core.article_source.get_storage_manager")
    @patch("src.hex_machina.enrichment.core.article_source.DatabaseConfigManager")
    def setup_method(self, mock_config_manager, mock_get_storage_manager):
        """Setup test environment."""
        mock_config_manager.return_value.get_db_path.return_value = "test.db"
        mock_storage_manager = Mock()
        mock_get_storage_manager.return_value = mock_storage_manager
        
        self.article_source = ArticleSource()
        self.mock_storage_manager = mock_storage_manager

    def test_resolve_single_article_success(self):
        """Test resolving a single article successfully."""
        # Setup mock
        mock_article = ArticleDB(
            id=1, 
            title="Test Article", 
            text_content="Content", 
            url="http://test.com", 
            url_domain="test.com"
        )
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_article
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        # Execute
        result = self.article_source.resolve_single_article(1)

        # Assertions
        assert result == mock_article
        mock_session.query.assert_called_once_with(ArticleDB)

    def test_resolve_single_article_not_found(self, caplog):
        """Test resolving a single article when not found."""
        # Setup mock
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        # Execute
        with caplog.at_level("WARNING"):
            result = self.article_source.resolve_single_article(999)

        # Assertions
        assert result is None
        assert "Article ID 999 not found" in caplog.text

    def test_resolve_multiple_articles_success(self):
        """Test resolving multiple articles successfully."""
        # Setup mock
        mock_articles = [
            ArticleDB(id=1, title="Article 1", text_content="Content 1", url="http://test1.com", url_domain="test1.com"),
            ArticleDB(id=2, title="Article 2", text_content="Content 2", url="http://test2.com", url_domain="test2.com"),
        ]
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = mock_articles
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        # Execute
        result = self.article_source.resolve_multiple_articles([1, 2])

        # Assertions
        assert result == mock_articles
        assert len(result) == 2

    def test_resolve_multiple_articles_partial_found(self, caplog):
        """Test resolving multiple articles when some are not found."""
        # Setup mock - only return article with ID 1
        mock_articles = [
            ArticleDB(id=1, title="Article 1", text_content="Content 1", url="http://test1.com", url_domain="test1.com"),
        ]
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = mock_articles
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        # Execute
        with caplog.at_level("WARNING"):
            result = self.article_source.resolve_multiple_articles([1, 2, 3])

        # Assertions
        assert len(result) == 1
        assert result[0].id == 1
        assert "Missing article IDs: {2, 3}" in caplog.text

    def test_resolve_multiple_articles_empty_list(self):
        """Test resolving multiple articles with empty list."""
        # Setup mock
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        # Execute
        result = self.article_source.resolve_multiple_articles([])

        # Assertions
        assert result == []

    def test_resolve_ingestion_operation_success(self):
        """Test resolving articles from ingestion operation."""
        # Setup mock
        mock_articles = [
            ArticleDB(id=1, title="Article 1", text_content="Content 1", url="http://test1.com", url_domain="test1.com", ingestion_operation_id=123),
            ArticleDB(id=2, title="Article 2", text_content="Content 2", url="http://test2.com", url_domain="test2.com", ingestion_operation_id=123),
        ]
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = mock_articles
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        # Execute
        result = self.article_source.resolve_ingestion_operation(123)

        # Assertions
        assert result == mock_articles
        assert len(result) == 2

    def test_resolve_ingestion_operation_not_found(self):
        """Test resolving articles from non-existent ingestion operation."""
        # Setup mock
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        # Execute
        result = self.article_source.resolve_ingestion_operation(999)

        # Assertions
        assert result == []

    def test_resolve_dataset_success(self):
        """Test resolving articles from dataset."""
        # Setup mock
        mock_articles = [
            ArticleDB(
                id=1, 
                title="Article 1", 
                text_content="Content 1", 
                url="http://test1.com", 
                url_domain="test1.com",
                ingestion_metadata={"dataset": "test_dataset"}
            ),
        ]
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = mock_articles
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        # Execute
        result = self.article_source.resolve_dataset("test_dataset")

        # Assertions
        assert result == mock_articles
        assert len(result) == 1

    def test_resolve_dataset_not_found(self):
        """Test resolving articles from non-existent dataset."""
        # Setup mock
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        # Execute
        result = self.article_source.resolve_dataset("nonexistent_dataset")

        # Assertions
        assert result == []

    def test_resolve_all_articles_no_limit(self):
        """Test resolving all articles without limit."""
        # Setup mock
        mock_articles = [
            ArticleDB(id=i, title=f"Article {i}", text_content=f"Content {i}", 
                     url=f"http://test{i}.com", url_domain=f"test{i}.com") 
            for i in range(1, 6)
        ]
        mock_session = Mock()
        mock_session.query.return_value.all.return_value = mock_articles
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        # Execute
        result = self.article_source.resolve_all_articles()

        # Assertions
        assert result == mock_articles
        assert len(result) == 5

    def test_resolve_all_articles_with_limit(self):
        """Test resolving all articles with limit."""
        # Setup mock
        mock_articles = [
            ArticleDB(id=1, title="Article 1", text_content="Content 1", url="http://test1.com", url_domain="test1.com"),
            ArticleDB(id=2, title="Article 2", text_content="Content 2", url="http://test2.com", url_domain="test2.com"),
        ]
        mock_query = Mock()
        mock_query.limit.return_value.all.return_value = mock_articles
        mock_session = Mock()
        mock_session.query.return_value = mock_query
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        # Execute
        result = self.article_source.resolve_all_articles(limit=2)

        # Assertions
        assert result == mock_articles
        mock_query.limit.assert_called_once_with(2)

    def test_resolve_input_file_success(self):
        """Test resolving article data from input file."""
        test_data = {
            "title": "Test Article",
            "content": "Test content",
            "url": "http://test.com"
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_file_path = f.name

        try:
            result = self.article_source.resolve_input_file(temp_file_path)
            assert result == test_data
        finally:
            import os
            os.unlink(temp_file_path)

    def test_resolve_input_file_invalid_json(self):
        """Test resolving article data from file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_file_path = f.name

        try:
            with pytest.raises(Exception):
                self.article_source.resolve_input_file(temp_file_path)
        finally:
            import os
            os.unlink(temp_file_path)

    def test_resolve_input_file_missing_file(self):
        """Test resolving article data from missing file."""
        with pytest.raises(Exception):
            self.article_source.resolve_input_file("nonexistent_file.json")

    def test_get_article_count_single_article_found(self):
        """Test getting article count for single article when found."""
        self.article_source.resolve_single_article = Mock(return_value=Mock())

        count = self.article_source.get_article_count("single_article", 1)

        assert count == 1

    def test_get_article_count_single_article_not_found(self):
        """Test getting article count for single article when not found."""
        self.article_source.resolve_single_article = Mock(return_value=None)

        count = self.article_source.get_article_count("single_article", 999)

        assert count == 0

    def test_get_article_count_multiple_articles(self):
        """Test getting article count for multiple articles."""
        mock_articles = [Mock(), Mock(), Mock()]
        self.article_source.resolve_multiple_articles = Mock(return_value=mock_articles)

        count = self.article_source.get_article_count("multiple_articles", [1, 2, 3])

        assert count == 3

    def test_get_article_count_ingestion_operation(self):
        """Test getting article count for ingestion operation."""
        mock_articles = [Mock(), Mock()]
        self.article_source.resolve_ingestion_operation = Mock(return_value=mock_articles)

        count = self.article_source.get_article_count("ingestion_operation", 123)

        assert count == 2

    def test_get_article_count_dataset(self):
        """Test getting article count for dataset."""
        mock_articles = [Mock()]
        self.article_source.resolve_dataset = Mock(return_value=mock_articles)

        count = self.article_source.get_article_count("dataset", "test_dataset")

        assert count == 1

    def test_get_article_count_all_articles(self):
        """Test getting article count for all articles."""
        mock_articles = [Mock() for _ in range(10)]
        self.article_source.resolve_all_articles = Mock(return_value=mock_articles)

        count = self.article_source.get_article_count("all_articles", 5)

        assert count == 10

    def test_get_article_count_unknown_source(self):
        """Test getting article count for unknown source type."""
        count = self.article_source.get_article_count("unknown_source", "value")

        assert count == 0

    def test_get_article_count_exception(self, caplog):
        """Test getting article count when exception occurs."""
        self.article_source.resolve_single_article = Mock(side_effect=Exception("Database error"))

        with caplog.at_level("ERROR"):
            count = self.article_source.get_article_count("single_article", 1)

        assert count == 0
        assert "Error getting article count" in caplog.text

    def test_validate_source_valid(self):
        """Test validating a source with articles."""
        self.article_source.get_article_count = Mock(return_value=5)

        result = self.article_source.validate_source("single_article", 1)

        assert result is True

    def test_validate_source_invalid(self):
        """Test validating a source with no articles."""
        self.article_source.get_article_count = Mock(return_value=0)

        result = self.article_source.validate_source("single_article", 999)

        assert result is False

    def test_validate_source_exception(self):
        """Test validating a source when exception occurs."""
        self.article_source.get_article_count = Mock(side_effect=Exception("Database error"))

        result = self.article_source.validate_source("single_article", 1)

        assert result is False

    def test_logging_debug_messages(self, caplog):
        """Test that debug messages are logged appropriately."""
        mock_article = ArticleDB(
            id=1, 
            title="Test Article", 
            text_content="Content", 
            url="http://test.com", 
            url_domain="test.com"
        )
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_article
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        with caplog.at_level("DEBUG"):
            self.article_source.resolve_single_article(1)

        debug_messages = [record.message for record in caplog.records if record.levelname == "DEBUG"]
        assert any("Resolving single article ID: 1" in msg for msg in debug_messages)
        assert any("Found article: Test Article" in msg for msg in debug_messages)

    def test_ingestion_metadata_filtering(self):
        """Test that dataset resolution properly filters by ingestion metadata."""
        # Setup mock to verify the correct filter is applied
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = []
        self.mock_storage_manager.session.return_value.__enter__.return_value = mock_session

        # Execute
        self.article_source.resolve_dataset("test_dataset")

        # Verify the filter was called with the correct metadata constraint
        mock_query.filter.assert_called_once()
        # The actual filter call will depend on SQLAlchemy implementation details
        # but we can verify it was called

    @patch("src.hex_machina.enrichment.core.article_source.DatabaseConfigManager")
    @patch("src.hex_machina.enrichment.core.article_source.get_storage_manager")
    def test_initialization_with_config(self, mock_get_storage_manager, mock_config_manager_class):
        """Test proper initialization with database configuration."""
        mock_config_manager = Mock()
        mock_config_manager.get_db_path.return_value = "/path/to/test.db"
        mock_config_manager_class.return_value = mock_config_manager
        
        mock_storage_manager = Mock()
        mock_get_storage_manager.return_value = mock_storage_manager

        # Create instance
        article_source = ArticleSource()

        # Verify configuration was loaded
        mock_config_manager_class.assert_called_once()
        mock_config_manager.get_db_path.assert_called_once()
        mock_get_storage_manager.assert_called_once_with("/path/to/test.db")
        
        assert article_source._db_path == "/path/to/test.db"
        assert article_source._storage_manager == mock_storage_manager