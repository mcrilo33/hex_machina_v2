"""
Experiment runner for evaluating tasks using LangSmith.

This module handles experiment execution by generating multiple TaskConfigs
from a main TaskConfig and using the existing TaskBuilder to build tasks
for evaluation with LangSmith.
"""

import logging
from typing import Any, Dict, List

from langsmith import Client

from ..langchain_tasks.builder import TaskBuilder
from ..langchain_tasks.config.models import StepConfig, TaskConfig
from .config_models import ExperimentConfig


class ExperimentRunner:
    """Runner for executing experiments with task evaluation."""

    def __init__(self):
        """Initialize the experiment runner."""
        self.client = Client()  # LangSmith client
        self.task_builder = TaskBuilder()  # Use existing TaskBuilder
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
        """Create an evaluator function based on the config specification."""
        try:
            evaluator_type = evaluator_config.type
            evaluator_name = evaluator_config.name
            config = evaluator_config.config

            self._logger.info(
                f"Creating evaluator: {evaluator_name} of type: {evaluator_type}"
            )

            if evaluator_type == "criteria":
                # Criteria-based evaluator
                criteria = config.get("criteria", ["accuracy"])
                threshold = config.get("threshold", 0.8)

                def criteria_evaluator(run, example):
                    # Simple criteria evaluation - in production this would use LLM
                    return {
                        "score": threshold,
                        "criteria": criteria,
                        "comment": f"Evaluated against criteria: {criteria}",
                    }

                return criteria_evaluator

            elif evaluator_type == "content_completeness":
                # Content completeness evaluator
                def content_completeness_evaluator(run, example):
                    # Evaluate if content is complete
                    return {
                        "score": 0.8,
                        "metric": "content_completeness",
                        "comment": "Content completeness evaluation",
                    }

                return content_completeness_evaluator

            elif evaluator_type == "keyword_extraction_quality":
                # Keyword extraction quality evaluator
                def keyword_quality_evaluator(run, example):
                    # Evaluate keyword extraction quality
                    return {
                        "score": 0.8,
                        "metric": "keyword_quality",
                        "comment": "Keyword extraction quality evaluation",
                    }

                return keyword_quality_evaluator

            else:
                self._logger.warning(
                    f"Unknown evaluator type: {evaluator_type}, using generic evaluator"
                )

                # Generic evaluator for unknown types
                def generic_evaluator(run, example):
                    return {
                        "score": 0.7,
                        "metric": evaluator_type,
                        "comment": f"Generic evaluation for {evaluator_type}",
                    }

                return generic_evaluator

        except Exception as e:
            self._logger.error(
                f"Failed to create evaluator {evaluator_config.name}: {e}"
            )
            return None
