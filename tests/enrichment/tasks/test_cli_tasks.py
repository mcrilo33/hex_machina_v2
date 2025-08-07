"""Tests for CLI tasks functionality."""

import json
import tempfile
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from src.hex_machina.cli.tasks.main import (
    tasks_cli,
    validate_source_options,
    _save_results_to_file,
    _show_results_summary,
)
from src.hex_machina.core.base import TaskOutput


class TestValidateSourceOptions:
    """Test source validation functionality."""

    def test_validate_single_source_valid(self):
        """Test validation with single valid source."""
        # Should not raise for single source
        validate_source_options(
            article_id=1,
            article_ids=None,
            ingestion_operation_id=None,
            dataset_name=None,
            all_articles=False,
            input_file=None,
        )

    def test_validate_no_source_error(self):
        """Test error when no source is specified."""
        with pytest.raises(Exception) as exc_info:
            validate_source_options(
                article_id=None,
                article_ids=None,
                ingestion_operation_id=None,
                dataset_name=None,
                all_articles=False,
                input_file=None,
            )
        assert "Must specify one article source" in str(exc_info.value)

    def test_validate_multiple_sources_error(self):
        """Test error when multiple sources are specified."""
        with pytest.raises(Exception) as exc_info:
            validate_source_options(
                article_id=1,
                article_ids="2,3",
                ingestion_operation_id=None,
                dataset_name=None,
                all_articles=False,
                input_file=None,
            )
        assert "Can only specify one article source" in str(exc_info.value)


class TestTasksCLI:
    """Test CLI commands."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    @patch("src.hex_machina.cli.tasks.main.task_runner")
    @patch("src.hex_machina.cli.tasks.main.ArticleSource")
    def test_run_command_single_article(self, mock_article_source, mock_task_runner):
        """Test run command with single article ID."""
        # Setup mocks
        mock_source = Mock()
        mock_source.validate_source.return_value = True
        mock_source.get_article_count.return_value = 1
        mock_article_source.return_value = mock_source

        mock_task_runner.run_task_on_source = AsyncMock(return_value=[])

        # Run command
        result = self.runner.invoke(
            tasks_cli, ["run", "--task", "test_task", "--article-id", "1"]
        )

        # Assertions
        assert result.exit_code == 0
        mock_source.validate_source.assert_called_once_with("single_article", 1)
        mock_task_runner.run_task_on_source.assert_called_once()

    @patch("src.hex_machina.cli.tasks.main.task_runner")
    @patch("src.hex_machina.cli.tasks.main.ArticleSource")
    def test_run_command_multiple_articles(self, mock_article_source, mock_task_runner):
        """Test run command with multiple article IDs."""
        # Setup mocks
        mock_source = Mock()
        mock_source.validate_source.return_value = True
        mock_source.get_article_count.return_value = 3
        mock_article_source.return_value = mock_source

        mock_task_runner.run_task_on_source = AsyncMock(return_value=[])

        # Run command
        result = self.runner.invoke(
            tasks_cli, ["run", "--task", "test_task", "--article-ids", "1,2,3"]
        )

        # Assertions
        assert result.exit_code == 0
        mock_source.validate_source.assert_called_once_with("multiple_articles", [1, 2, 3])

    def test_run_command_invalid_article_ids(self):
        """Test run command with invalid article IDs format."""
        result = self.runner.invoke(
            tasks_cli, ["run", "--task", "test_task", "--article-ids", "1,invalid,3"]
        )

        assert result.exit_code != 0
        assert "Invalid article IDs format" in result.output

    @patch("src.hex_machina.cli.tasks.main.task_runner")
    @patch("src.hex_machina.cli.tasks.main.ArticleSource")
    def test_run_command_dry_run(self, mock_article_source, mock_task_runner):
        """Test run command with dry-run flag."""
        # Setup mocks
        mock_source = Mock()
        mock_source.validate_source.return_value = True
        mock_source.get_article_count.return_value = 5
        mock_article_source.return_value = mock_source

        # Run command
        result = self.runner.invoke(
            tasks_cli, ["run", "--task", "test_task", "--article-id", "1", "--dry-run"]
        )

        # Assertions
        assert result.exit_code == 0
        assert "DRY RUN: Would process 5 articles" in result.output
        mock_task_runner.run_task_on_source.assert_not_called()

    @patch("src.hex_machina.cli.tasks.main.task_runner")
    @patch("src.hex_machina.cli.tasks.main.ArticleSource")
    def test_run_command_all_articles_no_confirm(self, mock_article_source, mock_task_runner):
        """Test run command with all articles but no confirm flag."""
        result = self.runner.invoke(
            tasks_cli, ["run", "--task", "test_task", "--all-articles"]
        )

        assert result.exit_code == 0
        assert "Use --confirm to proceed" in result.output
        mock_task_runner.run_task_on_source.assert_not_called()

    @patch("src.hex_machina.cli.tasks.main.task_runner")
    @patch("src.hex_machina.cli.tasks.main.ArticleSource")
    def test_run_command_all_articles_with_confirm(self, mock_article_source, mock_task_runner):
        """Test run command with all articles and confirm flag."""
        # Setup mocks
        mock_source = Mock()
        mock_source.validate_source.return_value = True
        mock_source.get_article_count.return_value = 100
        mock_article_source.return_value = mock_source

        mock_task_runner.run_task_on_source = AsyncMock(return_value=[])

        # Run command
        result = self.runner.invoke(
            tasks_cli, ["run", "--task", "test_task", "--all-articles", "--confirm"]
        )

        # Assertions
        assert result.exit_code == 0
        mock_task_runner.run_task_on_source.assert_called_once()

    @patch("src.hex_machina.cli.tasks.main.task_runner")
    @patch("src.hex_machina.cli.tasks.main.ArticleSource")
    def test_run_command_no_articles_found(self, mock_article_source, mock_task_runner):
        """Test run command when no articles are found."""
        # Setup mocks
        mock_source = Mock()
        mock_source.validate_source.return_value = False
        mock_article_source.return_value = mock_source

        # Run command
        result = self.runner.invoke(
            tasks_cli, ["run", "--task", "test_task", "--article-id", "999"]
        )

        # Assertions
        assert result.exit_code == 0
        assert "No articles found" in result.output
        mock_task_runner.run_task_on_source.assert_not_called()

    @patch("src.hex_machina.cli.tasks.main._run_task_on_input_file")
    def test_run_command_input_file(self, mock_run_task):
        """Test run command with input file (legacy)."""
        mock_run_task.return_value = None

        result = self.runner.invoke(
            tasks_cli, ["run", "--task", "test_task", "--input-file", "test.json"]
        )

        assert result.exit_code == 0
        mock_run_task.assert_called_once()

    @patch("src.hex_machina.cli.tasks.main.task_runner")
    def test_list_tasks_command(self, mock_task_runner):
        """Test list-tasks command."""
        mock_task_runner._task_registry.list_tasks.return_value = ["task1", "task2"]

        result = self.runner.invoke(tasks_cli, ["list-tasks"])

        assert result.exit_code == 0
        assert "task1" in result.output
        assert "task2" in result.output

    def test_list_runs_command(self):
        """Test list-runs command."""
        result = self.runner.invoke(tasks_cli, ["list-runs"])

        assert result.exit_code == 0
        assert "Recent task runs" in result.output

    def test_show_run_command(self):
        """Test show-run command."""
        result = self.runner.invoke(tasks_cli, ["show-run", "test-task-id"])

        assert result.exit_code == 0
        assert "test-task-id" in result.output

    def test_stats_command(self):
        """Test stats command."""
        result = self.runner.invoke(tasks_cli, ["stats"])

        assert result.exit_code == 0
        assert "Task Statistics" in result.output


class TestResultsHandling:
    """Test results handling functions."""

    def test_save_results_to_file_json(self):
        """Test saving results to JSON file."""
        # Create test results
        results = [
            TaskOutput(
                task_id="test1",
                output_data={"result": "success"},
                metadata={"task_name": "test_task"},
                execution_time=1.5,
                created_at="2024-01-01T12:00:00",
            ),
            TaskOutput(
                task_id="test2",
                output_data={"result": "error"},
                metadata={"task_name": "test_task"},
                execution_time=0.8,
                error="Test error",
                created_at="2024-01-01T12:01:00",
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            _save_results_to_file(results, temp_dir, "json")

            # Check file was created
            import os
            files = os.listdir(temp_dir)
            assert len(files) == 1
            assert files[0].startswith("task_results_")
            assert files[0].endswith(".json")

            # Check file content
            with open(os.path.join(temp_dir, files[0]), "r") as f:
                data = json.load(f)
            assert len(data) == 2
            assert data[0]["task_id"] == "test1"

    def test_save_results_to_file_csv(self):
        """Test saving results to CSV file."""
        # Create test results
        results = [
            TaskOutput(
                task_id="test1",
                output_data={"result": "success"},
                metadata={"task_name": "test_task"},
                execution_time=1.5,
                created_at="2024-01-01T12:00:00",
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            _save_results_to_file(results, temp_dir, "csv")

            # Check file was created
            import os
            files = os.listdir(temp_dir)
            assert len(files) == 1
            assert files[0].startswith("task_results_")
            assert files[0].endswith(".csv")

    def test_show_results_summary_empty(self, capsys):
        """Test showing summary with empty results."""
        _show_results_summary([])
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_show_results_summary_mixed(self, capsys):
        """Test showing summary with mixed success/failure results."""
        results = [
            TaskOutput(
                task_id="test1",
                output_data={"result": "success"},
                metadata={"task_name": "test_task"},
                execution_time=1.5,
                created_at="2024-01-01T12:00:00",
            ),
            TaskOutput(
                task_id="test2",
                output_data={},
                metadata={"task_name": "test_task"},
                execution_time=0.8,
                error="Test error",
                created_at="2024-01-01T12:01:00",
            ),
            TaskOutput(
                task_id="test3",
                output_data={"result": "success"},
                metadata={"task_name": "test_task"},
                execution_time=2.1,
                created_at="2024-01-01T12:02:00",
            ),
        ]

        _show_results_summary(results)
        captured = capsys.readouterr()

        assert "Successful: 2" in captured.out
        assert "Failed: 1" in captured.out
        assert "Average execution time: 1.80s" in captured.out
        assert "test2: Test error" in captured.out


@pytest.mark.asyncio
class TestInputFileHandling:
    """Test input file handling functionality."""

    @patch("src.hex_machina.cli.tasks.main.task_runner")
    async def test_run_task_on_input_file_success(self, mock_task_runner):
        """Test running task on input file successfully."""
        from src.hex_machina.cli.tasks.main import _run_task_on_input_file

        # Create test input file
        test_data = {"title": "Test Article", "content": "Test content"}
        mock_result = TaskOutput(
            task_id="test",
            output_data={"result": "success"},
            metadata={},
            execution_time=1.0,
            created_at="2024-01-01T12:00:00",
        )

        mock_task_runner.run_task = AsyncMock(return_value=mock_result)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_file_path = f.name

        try:
            await _run_task_on_input_file("test_task", temp_file_path)
            mock_task_runner.run_task.assert_called_once_with("test_task", test_data)
        finally:
            import os
            os.unlink(temp_file_path)

    async def test_run_task_on_input_file_invalid_json(self, capsys):
        """Test running task on input file with invalid JSON."""
        from src.hex_machina.cli.tasks.main import _run_task_on_input_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_file_path = f.name

        try:
            await _run_task_on_input_file("test_task", temp_file_path)
            captured = capsys.readouterr()
            assert "Error running task" in captured.out
        finally:
            import os
            os.unlink(temp_file_path)

    async def test_run_task_on_input_file_missing_file(self, capsys):
        """Test running task on missing input file."""
        from src.hex_machina.cli.tasks.main import _run_task_on_input_file

        await _run_task_on_input_file("test_task", "nonexistent_file.json")
        captured = capsys.readouterr()
        assert "Error running task" in captured.out