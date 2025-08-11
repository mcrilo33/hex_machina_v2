"""Tests for content completeness task implementation."""

import pytest
from unittest.mock import Mock

from src.hex_machina.core.base import TaskInput
from src.hex_machina.enrichment.tasks.content_completeness_langchain import (
    ContentCompletenessLangChainTask,
)
from src.hex_machina.enrichment.tasks.base.langchain_task import LangChainTaskConfig


class TestContentCompletenessLangChainTask:
    """Test ContentCompletenessLangChainTask functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.config = LangChainTaskConfig(
            llm_provider="openrouter",
            llm_model="test-model",
            prompt_template="Evaluate completeness: {content}",
        )
        self.task = ContentCompletenessLangChainTask(self.config)

    def test_task_initialization(self):
        """Test task initialization."""
        assert self.task.name == "content_completeness_langchain"
        assert self.task.config == self.config

    def test_validate_input_valid(self):
        """Test input validation with valid data."""
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={
                "title": "Test Article",
                "content": "This is test content with substantial information.",
            },
        )

        result = self.task.validate_input(task_input)

        assert result is True

    def test_validate_input_missing_title(self, caplog):
        """Test input validation when title is missing."""
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={
                "content": "This is test content.",
            },
        )

        with caplog.at_level("ERROR"):
            result = self.task.validate_input(task_input)

        assert result is False
        assert "Missing 'title' in input data" in caplog.text

    def test_validate_input_missing_content(self, caplog):
        """Test input validation when content is missing."""
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={
                "title": "Test Article",
            },
        )

        with caplog.at_level("ERROR"):
            result = self.task.validate_input(task_input)

        assert result is False
        assert "Missing 'content' in input data" in caplog.text

    def test_validate_input_empty_content(self, caplog):
        """Test input validation when content is empty."""
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={
                "title": "Test Article",
                "content": "",
            },
        )

        with caplog.at_level("ERROR"):
            result = self.task.validate_input(task_input)

        assert result is False
        assert "Content is empty" in caplog.text

    def test_validate_input_whitespace_only_content(self, caplog):
        """Test input validation when content is only whitespace."""
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={
                "title": "Test Article",
                "content": "   \n\t   ",
            },
        )

        with caplog.at_level("ERROR"):
            result = self.task.validate_input(task_input)

        assert result is False
        assert "Content is empty" in caplog.text

    def test_validate_input_exception_handling(self, caplog):
        """Test input validation exception handling."""
        # Create malformed input that causes exception
        task_input = Mock()
        task_input.input_data = None  # This will cause a TypeError

        with caplog.at_level("ERROR"):
            result = self.task.validate_input(task_input)

        assert result is False
        assert "Error validating input" in caplog.text

    def test_get_default_parser_name(self):
        """Test getting default parser name."""
        result = self.task.get_default_parser_name()

        assert result == "CompletenessOutputParser"

    def test_validate_input_with_additional_fields(self):
        """Test input validation with additional fields (should still pass)."""
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={
                "title": "Test Article",
                "content": "This is test content.",
                "url": "http://example.com",
                "author": "Test Author",
                "metadata": {"key": "value"},
            },
        )

        result = self.task.validate_input(task_input)

        assert result is True

    def test_validate_input_none_content(self, caplog):
        """Test input validation when content is None."""
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={
                "title": "Test Article",
                "content": None,
            },
        )

        with caplog.at_level("ERROR"):
            result = self.task.validate_input(task_input)

        assert result is False
        assert "Content is empty" in caplog.text

    def test_validate_input_with_minimal_valid_content(self):
        """Test input validation with minimal valid content."""
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={
                "title": "Test",
                "content": "x",  # Single character content
            },
        )

        result = self.task.validate_input(task_input)

        assert result is True

    def test_validate_input_unicode_content(self):
        """Test input validation with unicode content."""
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={
                "title": "Unicode Test 🔥",
                "content": "Content with emojis 🚀 and unicode characters ñ á é",
            },
        )

        result = self.task.validate_input(task_input)

        assert result is True

    def test_validate_input_numeric_values(self):
        """Test input validation when title/content are numeric."""
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={
                "title": 12345,  # Numeric title
                "content": 67890,  # Numeric content
            },
        )

        # Should still validate since they convert to truthy strings
        result = self.task.validate_input(task_input)

        assert result is True

    def test_validate_input_very_long_content(self):
        """Test input validation with very long content."""
        long_content = "x" * 100000  # 100k characters
        
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={
                "title": "Long Content Test",
                "content": long_content,
            },
        )

        result = self.task.validate_input(task_input)

        assert result is True

    def test_task_inheritance(self):
        """Test that task properly inherits from LangChainTask."""
        from src.hex_machina.enrichment.tasks.base.langchain_task import LangChainTask
        
        assert isinstance(self.task, LangChainTask)
        assert hasattr(self.task, 'initialize')
        assert hasattr(self.task, 'execute')
        assert hasattr(self.task, '_initialize_llm')
        assert hasattr(self.task, '_initialize_prompt_template')
        assert hasattr(self.task, '_initialize_output_parser')

    def test_task_name_consistency(self):
        """Test that task name is consistent."""
        # Test with different config
        config2 = LangChainTaskConfig(
            llm_provider="openai",
            llm_model="different-model",
            prompt_template="Different template",
        )
        
        task2 = ContentCompletenessLangChainTask(config2)
        
        # Both instances should have the same task name
        assert self.task.name == task2.name
        assert self.task.name == "content_completeness_langchain"

    def test_parser_name_consistency(self):
        """Test that parser name is consistent across instances."""
        config2 = LangChainTaskConfig(
            llm_provider="openai",
            llm_model="different-model",
            prompt_template="Different template",
        )
        
        task2 = ContentCompletenessLangChainTask(config2)
        
        # Both instances should return the same parser name
        assert self.task.get_default_parser_name() == task2.get_default_parser_name()
        assert self.task.get_default_parser_name() == "CompletenessOutputParser"