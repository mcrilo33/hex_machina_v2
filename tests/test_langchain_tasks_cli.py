"""
Tests for the langchain_tasks CLI.

This module tests the CLI functionality for running tasks and experiments.
"""

from unittest.mock import Mock, patch

import pytest

from src.hex_machina.langchain_tasks.cli import (
    load_yaml_config,
    run_experiment,
    run_task,
    validate_yaml_config,
)


class TestCLI:
    """Test cases for the CLI functionality."""

    def test_validate_yaml_config_valid_file(self, tmp_path):
        """Test validation of valid YAML config file."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("name: test")

        result = validate_yaml_config(config_file)
        assert result == config_file

    def test_validate_yaml_config_file_not_found(self, tmp_path):
        """Test validation fails for non-existent file."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            validate_yaml_config(config_file)

    def test_validate_yaml_config_invalid_extension(self, tmp_path):
        """Test validation fails for non-YAML file."""
        config_file = tmp_path / "test.txt"
        config_file.write_text("name: test")

        with pytest.raises(ValueError, match="must be YAML"):
            validate_yaml_config(config_file)

    def test_load_yaml_config_success(self, tmp_path):
        """Test successful YAML loading."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("name: test\ndescription: test config")

        result = load_yaml_config(config_file)
        assert result == {"name": "test", "description": "test config"}

    def test_load_yaml_config_invalid_yaml(self, tmp_path):
        """Test YAML loading fails for invalid YAML."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("name: test\n  invalid: yaml: content")

        with pytest.raises(Exception):
            load_yaml_config(config_file)

    @patch("src.hex_machina.langchain_tasks.cli.RunnableRegistry")
    @patch("src.hex_machina.langchain_tasks.cli.TaskBuilder")
    def test_run_task_success(self, mock_task_builder, mock_registry, tmp_path):
        """Test successful task execution."""
        # Setup mocks
        mock_registry_instance = Mock()
        mock_registry.return_value = mock_registry_instance

        mock_builder_instance = Mock()
        mock_task_builder.return_value = mock_builder_instance

        mock_task = Mock()
        mock_builder_instance.invoke.return_value = mock_task
        mock_task.invoke.return_value = {"result": "success"}

        # Create test config
        config_file = tmp_path / "task.yaml"
        config_file.write_text("name: test_task\nsteps: []")

        # Execute
        run_task(config_file)

        # Verify
        mock_builder_instance.invoke.assert_called_once()
        mock_task.invoke.assert_called_once_with({})

    @patch("src.hex_machina.langchain_tasks.cli.RunnableRegistry")
    @patch("src.hex_machina.langchain_tasks.cli.TaskBuilder")
    def test_run_task_with_article_id(self, mock_task_builder, mock_registry, tmp_path):
        """Test task execution with article ID."""
        # Setup mocks
        mock_registry_instance = Mock()
        mock_registry.return_value = mock_registry_instance

        mock_builder_instance = Mock()
        mock_task_builder.return_value = mock_builder_instance

        mock_task = Mock()
        mock_builder_instance.invoke.return_value = mock_task
        mock_task.invoke.return_value = {"result": "success"}

        # Create test config
        config_file = tmp_path / "task.yaml"
        config_file.write_text("name: test_task\nsteps: []")

        # Execute with article ID
        run_task(config_file, article_id=123)

        # Verify
        mock_task.invoke.assert_called_once_with({"article_id": 123})

    @patch("src.hex_machina.langchain_tasks.cli.RunnableRegistry")
    @patch("src.hex_machina.langchain_tasks.cli.TaskBuilder")
    @patch("src.hex_machina.langchain_tasks.cli.ExperimentRunner")
    def test_run_experiment_success(
        self, mock_experiment_runner, mock_task_builder, mock_registry, tmp_path
    ):
        """Test successful experiment execution."""
        # Setup mocks
        mock_registry_instance = Mock()
        mock_registry.return_value = mock_registry_instance

        mock_builder_instance = Mock()
        mock_task_builder.return_value = mock_builder_instance

        mock_runner_instance = Mock()
        mock_experiment_runner.return_value = mock_runner_instance
        mock_runner_instance.run_experiment.return_value = {
            "total_variations": 3,
            "datasets_created": ["dataset1", "dataset2"],
        }

        # Create test config
        config_file = tmp_path / "experiment.yaml"
        config_file.write_text(
            "name: test_experiment\ntask:\n  name: test_task\n  steps: []"
        )

        # Execute
        run_experiment(config_file)

        # Verify
        mock_runner_instance.run_experiment.assert_called_once()

    @patch("src.hex_machina.langchain_tasks.cli.RunnableRegistry")
    @patch("src.hex_machina.langchain_tasks.cli.TaskBuilder")
    @patch("src.hex_machina.langchain_tasks.cli.ExperimentRunner")
    def test_run_experiment_with_input_file(
        self, mock_experiment_runner, mock_task_builder, mock_registry, tmp_path
    ):
        """Test experiment execution with input file."""
        # Setup mocks
        mock_registry_instance = Mock()
        mock_registry.return_value = mock_registry_instance

        mock_builder_instance = Mock()
        mock_task_builder.return_value = mock_builder_instance

        mock_runner_instance = Mock()
        mock_experiment_runner.return_value = mock_runner_instance
        mock_runner_instance.run_experiment.return_value = {
            "total_variations": 2,
            "datasets_created": ["dataset1"],
        }

        # Create test config and input file
        config_file = tmp_path / "experiment.yaml"
        config_file.write_text(
            "name: test_experiment\ntask:\n  name: test_task\n  steps: []"
        )

        input_file = tmp_path / "inputs.json"
        input_file.write_text('{"test": "data"}')

        # Execute with input file
        run_experiment(config_file, input_file=input_file)

        # Verify
        mock_runner_instance.run_experiment.assert_called_once()
        # Check that inputs were loaded (this would be verified in the actual implementation)
