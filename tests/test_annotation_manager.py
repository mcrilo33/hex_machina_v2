"""
Tests for the annotation manager.

This module tests the functionality of the annotation session manager
for interactive dataset annotation.
"""

from unittest.mock import Mock, patch

import pytest

from src.hex_machina.langchain_tasks.datasets.annotation_manager import (
    AnnotationManager,
)


class TestAnnotationManager:
    """Test cases for AnnotationManager."""

    def test_init(self):
        """Test AnnotationManager initialization."""
        manager = AnnotationManager()
        assert manager.TRUNCATION_LENGTH == 5000
        assert manager.DISPLAY_WIDTH == 80

    def test_truncate_text_short(self):
        """Test text truncation with short text."""
        manager = AnnotationManager()
        text = "Short text"
        result = manager._truncate_text(text)
        assert result == text

    def test_truncate_text_long(self):
        """Test text truncation with long text."""
        manager = AnnotationManager()
        text = "A" * 6000  # 6000 characters
        result = manager._truncate_text(text)
        # Account for the truncation text length
        assert len(result) <= 5000 + len("... [truncated] ...")
        assert "... [truncated] ..." in result

    def test_get_nested_field_value_simple(self):
        """Test getting simple field values."""
        manager = AnnotationManager()
        obj = {"simple_field": "value"}
        result = manager._get_nested_field_value(obj, "simple_field")
        assert result == "value"

    def test_get_nested_field_value_nested(self):
        """Test getting nested field values with bracket notation."""
        manager = AnnotationManager()
        obj = {"metadata": {"source_domain": "example.com"}}
        result = manager._get_nested_field_value(obj, "metadata['source_domain']")
        assert result == "example.com"

    def test_get_nested_field_value_missing(self):
        """Test getting missing nested field values."""
        manager = AnnotationManager()
        obj = {"metadata": {"other_field": "value"}}
        result = manager._get_nested_field_value(obj, "metadata['source_domain']")
        assert result is None

    def test_display_field_empty(self):
        """Test displaying empty field values."""
        manager = AnnotationManager()
        result = manager._display_field("test_field", None)
        assert result == "test_field: [EMPTY]"

    def test_display_field_string(self):
        """Test displaying string field values."""
        manager = AnnotationManager()
        result = manager._display_field("test_field", "test_value")
        assert result == "test_field: test_value"

    def test_display_field_non_string(self):
        """Test displaying non-string field values."""
        manager = AnnotationManager()
        result = manager._display_field("test_field", 42)
        assert result == "test_field: 42"

    @patch("builtins.input")
    def test_collect_annotations_categorical(self, mock_input):
        """Test collecting categorical annotations."""
        manager = AnnotationManager()
        mock_input.return_value = "high"

        # Mock config with categorical field
        mock_field = Mock()
        mock_field.name = "quality"
        mock_field.field_type = "categorical"
        mock_field.options = ["high", "medium", "low"]

        config = Mock()
        config.annotation_fields = {"inputs": [mock_field], "outputs": []}

        result = manager._collect_annotations(config)
        assert result["inputs"]["quality"] == "high"

    @patch("builtins.input")
    def test_collect_annotations_free_text(self, mock_input):
        """Test collecting free text annotations."""
        manager = AnnotationManager()
        mock_input.return_value = "This is a note"

        # Mock config with free text field
        mock_field = Mock()
        mock_field.name = "notes"
        mock_field.field_type = "free_text"
        mock_field.options = "free_text"

        config = Mock()
        config.annotation_fields = {"inputs": [], "outputs": [mock_field]}

        result = manager._collect_annotations(config)
        assert result["outputs"]["notes"] == "This is a note"


if __name__ == "__main__":
    pytest.main([__file__])
