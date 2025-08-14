"""
Tests for the experiment runner split functionality.
"""

from unittest.mock import Mock

import pytest

from src.hex_machina.experiments.config_models import EvaluatorConfig, ExperimentConfig
from src.hex_machina.experiments.runner import ExperimentRunner
from src.hex_machina.langchain_tasks.config.models import StepConfig, TaskConfig


class TestExperimentRunnerSplit:
    """Test split functionality in ExperimentRunner."""

    @pytest.fixture
    def basic_experiment_config(self):
        """Create a basic experiment configuration."""
        return ExperimentConfig(
            name="test_experiment",
            description="Test experiment",
            target_dataset="test_dataset",
            task=TaskConfig(
                name="test_task",
                description="Test task",
                steps=[
                    StepConfig(name="test_step", runnable="TestRunnable", config={})
                ],
            ),
            evaluators=[
                EvaluatorConfig(
                    name="test_evaluator",
                    type="criteria",
                    description="Test evaluator",
                    config={},
                )
            ],
        )

    @pytest.fixture
    def experiment_config_with_splits(self, basic_experiment_config):
        """Create an experiment configuration with splits specified."""
        config = basic_experiment_config.model_copy(deep=True)
        config.split = ["test", "training"]
        return config

    @pytest.fixture
    def experiment_config_single_split(self, basic_experiment_config):
        """Create an experiment configuration with a single split."""
        config = basic_experiment_config.model_copy(deep=True)
        config.split = "test"
        return config

    @pytest.mark.asyncio
    async def test_load_dataset_with_splits(self, experiment_config_with_splits):
        """Test loading dataset with multiple splits specified."""
        # Create runner and mock its client
        runner = ExperimentRunner()
        mock_client = Mock()
        mock_client.list_examples.return_value = [
            Mock(),
            Mock(),
            Mock(),
        ]  # 3 mock examples
        runner.client = mock_client

        # Test loading dataset with splits
        result = await runner._load_existing_dataset(experiment_config_with_splits)

        # Verify list_examples was called with correct parameters
        mock_client.list_examples.assert_called_once_with(
            dataset_name="test_dataset", splits=["test", "training"]
        )

        # Verify result is a list of examples
        assert isinstance(result, list)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_load_dataset_single_split(self, experiment_config_single_split):
        """Test loading dataset with a single split specified."""
        # Create runner and mock its client
        runner = ExperimentRunner()
        mock_client = Mock()
        mock_client.list_examples.return_value = [Mock(), Mock()]  # 2 mock examples
        runner.client = mock_client

        # Test loading dataset with single split
        result = await runner._load_existing_dataset(experiment_config_single_split)

        # Verify list_examples was called with correct parameters
        mock_client.list_examples.assert_called_once_with(
            dataset_name="test_dataset", splits=["test"]
        )

        # Verify result is a list of examples
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_load_dataset_no_splits(self, basic_experiment_config):
        """Test loading dataset without splits specified (backward compatibility)."""
        # Create runner and mock its client
        runner = ExperimentRunner()
        mock_client = Mock()
        runner.client = mock_client

        # Test loading dataset without splits
        result = await runner._load_existing_dataset(basic_experiment_config)

        # Verify list_examples was not called
        mock_client.list_examples.assert_not_called()

        # Verify result is the dataset name (backward compatibility)
        assert result == "test_dataset"

    def test_split_field_types(self):
        """Test that split field accepts different types correctly."""
        # Test with list of strings
        config_list = ExperimentConfig(
            name="test",
            description="test",
            target_dataset="test",
            task=TaskConfig(name="test", description="test", steps=[]),
            evaluators=[],
            split=["test", "training"],
        )
        assert config_list.split == ["test", "training"]

        # Test with single string
        config_single = ExperimentConfig(
            name="test",
            description="test",
            target_dataset="test",
            task=TaskConfig(name="test", description="test", steps=[]),
            evaluators=[],
            split="test",
        )
        assert config_single.split == "test"

        # Test with None (default)
        config_none = ExperimentConfig(
            name="test",
            description="test",
            target_dataset="test",
            task=TaskConfig(name="test", description="test", steps=[]),
            evaluators=[],
        )
        assert config_none.split is None
