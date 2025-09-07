"""
Experiment runner for evaluating tasks using LangSmith.

This module handles experiment execution by generating multiple TaskConfigs
from a main TaskConfig and using the existing TaskBuilder to build tasks
for evaluation with LangSmith.
"""

import logging
from typing import Any, Dict, List

from langsmith import Client, traceable

from ..langchain_tasks.builder import TaskBuilder
from ..langchain_tasks.config.models import StepConfig, TaskConfig
from .config_models import ExperimentConfig


class ExperimentRunner:
    """Runner for executing experiments with task evaluation."""

    def __init__(self, enable_caching: bool = True):
        """Initialize the experiment runner.

        Args:
            enable_caching: Whether to enable SQLite caching for LLM calls
        """
        self.client = Client()  # LangSmith client
        # Pass caching preference to TaskBuilder
        self.task_builder = TaskBuilder(enable_caching=enable_caching)
        self._logger = logging.getLogger(__name__)

        self._logger.info("ExperimentRunner initialized")

    async def run_experiment(self, config: ExperimentConfig) -> Dict[str, Any]:
        """Run an experiment by evaluating multiple task variations.

        Args:
            config: Experiment configuration

        Returns:
            Dictionary containing experiment results
        """
        self._logger.info(f"Starting experiment: {config.name}")

        try:
            # 1. Load existing target dataset
            target_dataset = await self._load_existing_dataset(config)

            # 2. Generate multiple TaskConfigs from the main TaskConfig
            task_variations = self._generate_task_variations(config.task)

            # 3. Build tasks using existing TaskBuilder
            targets = []
            for task_config in task_variations:
                task = self.task_builder.invoke(task_config)
                targets.append(task)

            # 4. Run evaluation using LangSmith aevaluate
            evaluation_results = []
            for i, target in enumerate(targets):
                self._logger.info(
                    f"Evaluating target {i+1}/{len(targets)}: {task_variations[i].name}"
                )

                # Convert evaluators to LangSmith format
                langsmith_evaluators = []
                for evaluator in config.evaluators:
                    # Create evaluator config for LangSmith
                    evaluator_config = {
                        "name": evaluator.name,
                        "type": evaluator.type,
                        "description": evaluator.description,
                        **evaluator.config,
                    }
                    langsmith_evaluators.append(evaluator_config)

                try:
                    # Use the correct LangSmith aevaluate method to create experiments
                    self._logger.info(
                        f"Creating experiment in LangSmith for target {i+1}"
                    )

                    # Create evaluators based on the config specifications
                    evaluators = []
                    for evaluator_config in config.evaluators:
                        evaluator = self._create_evaluator_from_config(evaluator_config)
                        if evaluator:
                            evaluators.append(evaluator)

                    if not evaluators:
                        self._logger.warning(
                            "No valid evaluators found, using default evaluator"
                        )

                        # Fallback to a simple evaluator if none are valid
                        def default_evaluator(run, example):
                            return {"score": 0.5, "comment": "Default evaluation"}

                        evaluators = [default_evaluator]

                    # Use the aevaluate method with only supported parameters
                    # Based on the LangSmith documentation: aevaluate(target, /[, data, evaluators, ...])
                    from langsmith import trace

                    with trace(
                        name=f"Exp {i+1}: {config.name}",
                        run_type="chain",
                        project_name="hex-machina-v2",
                        metadata=config.metadata,
                        tags=[f"exp:{config.name}"],
                    ) as run_tree:
                        result = await self.client.aevaluate(
                            target,  # First positional argument
                            data=target_dataset,
                            evaluators=evaluators,
                            experiment_prefix=config.name,  # Use experiment name as prefix
                        )

                    evaluation_results.append(result)
                    self._logger.info(
                        f"Successfully created experiment in LangSmith for target {i+1}"
                    )

                except Exception as eval_error:
                    self._logger.error(
                        f"Failed to create experiment in LangSmith for target {i+1}: {eval_error}"
                    )
                    # Continue with other targets instead of failing completely
                    evaluation_results.append({"error": str(eval_error)})

            self._logger.info(f"Experiment {config.name} completed successfully")

            return {
                "target_dataset": target_dataset,
                "task_variations": task_variations,
                "targets": targets,
                "evaluation_results": evaluation_results,
            }

        except Exception as e:
            self._logger.error(f"Experiment {config.name} failed: {e}")
            raise

    def _generate_task_variations(self, task_config: TaskConfig) -> List[TaskConfig]:
        """Generate multiple TaskConfigs from the main TaskConfig.

        Args:
            task_config: Base task configuration

        Returns:
            List of task configuration variations
        """
        variations = []

        # Generate variation for complete task execution
        complete_task = task_config.model_copy(deep=True)
        variations.append(complete_task)

        # Generate variations for individual steps if they have dataset=True
        for step in task_config.steps:
            if step.dataset:
                step_task = self._create_step_task_config(task_config, step)
                variations.append(step_task)

        self._logger.info(f"Generated {len(variations)} task variations")
        return variations

    def _create_step_task_config(
        self, task_config: TaskConfig, target_step: StepConfig
    ) -> TaskConfig:
        """Create a TaskConfig for evaluating just one step.

        Args:
            task_config: Original task configuration
            target_step: Step to create a task for

        Returns:
            New TaskConfig with only the target step
        """
        step_task = TaskConfig(
            name=f"{task_config.name}_{target_step.name}_evaluation",
            description=f"Evaluation of {target_step.name} step from {task_config.name}",
            steps=[target_step],  # Only include the target step
            metadata=task_config.metadata,
        )
        return step_task

    async def _load_existing_dataset(self, config: ExperimentConfig) -> Any:
        """Load existing dataset from LangSmith.

        Args:
            config: Experiment configuration containing dataset and split information

        Returns:
            Dataset data for evaluation (either dataset name or filtered examples)
        """
        try:
            dataset_name = config.target_dataset
            self._logger.info(f"Loading dataset: {dataset_name}")

            # If splits are specified, load examples with those splits
            if config.split:
                splits = (
                    [config.split] if isinstance(config.split, str) else config.split
                )
                self._logger.info(f"Loading examples from splits: {splits}")

                # Use list_examples to get examples from specific splits
                examples = self.client.list_examples(
                    dataset_name=dataset_name, splits=splits
                )

                # Convert generator to list for evaluation
                examples_list = list(examples)
                self._logger.info(
                    f"Loaded {len(examples_list)} examples from splits: {splits}"
                )
                return examples_list
            else:
                # Return dataset name for backward compatibility
                self._logger.info(
                    f"No splits specified, using entire dataset: {dataset_name}"
                )
                return dataset_name

        except Exception as e:
            self._logger.error(f"Failed to load dataset {config.target_dataset}: {e}")
            raise

    def _create_evaluator_from_config(self, evaluator_config):
        """Create an evaluator using the EvaluatorRegistry."""
        try:
            evaluator_type = evaluator_config.type
            evaluator_name = evaluator_config.name
            config = evaluator_config.config

            self._logger.info(
                f"Creating evaluator: {evaluator_name} of type: {evaluator_type}"
            )

            # Use the EvaluatorRegistry to get the evaluator
            from ..langchain_tasks.evaluation.registry import evaluator_registry

            try:
                # Try to get evaluator by type first
                evaluator = evaluator_registry.get_evaluator(evaluator_type, **config)
                self._logger.info(f"Successfully created evaluator: {evaluator_type}")
                return evaluator
            except ValueError as type_error:
                self._logger.warning(
                    f"Failed to create evaluator by type '{evaluator_type}': {type_error}"
                )
                # Fallback: try to get by name if type lookup fails
                try:
                    evaluator = evaluator_registry.get_evaluator(
                        evaluator_name, **config
                    )
                    self._logger.info(
                        f"Successfully created evaluator by name: {evaluator_name}"
                    )
                    return evaluator
                except ValueError as name_error:
                    # Fail fast - no generic fallback
                    error_msg = f"Failed to create evaluator '{evaluator_name}' of type '{evaluator_type}'. Type lookup failed: {type_error}, Name lookup failed: {name_error}"
                    self._logger.error(error_msg)
                    raise ValueError(error_msg)

        except Exception as e:
            self._logger.error(
                f"Failed to create evaluator {evaluator_config.name}: {e}"
            )
            raise
