"""
YAML-based experiment runner for LangSmith integration.

This module provides a runner that can execute experiments defined in YAML
configuration files using LangSmith's aevaluate, including task variations.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from langchain_core.runnables import RunnableLambda
from langsmith import Client, aevaluate

from .config_models import ExperimentConfiguration, TaskConfig
from .evaluator_factory import evaluator_factory


class YAMLExperimentRunner:
    """Runner for executing experiments defined in YAML configuration."""

    def __init__(self, client: Optional[Client] = None):
        """Initialize the YAML experiment runner."""
        self.client = client or Client()
        self._logger = logging.getLogger("langchain_tasks.experiments.yaml_runner")

    async def run_experiments_from_config(
        self, config: ExperimentConfiguration
    ) -> Dict[str, Any]:
        """Run all experiments defined in the configuration."""
        self._logger.info(f"Starting experiments from configuration: {config.name}")

        # Generate task variations
        task_variations = config.generate_task_variations()
        self._logger.info(f"Generated {len(task_variations)} task variations")

        results = {
            "configuration_name": config.name,
            "total_variations": len(task_variations),
            "variations": {},
            "summary": {"successful": 0, "failed": 0, "total_runs": 0},
        }

        # Run each task variation
        for i, task_variation in enumerate(task_variations):
            self._logger.info(f"Running task variation {i+1}: {task_variation.name}")

            variation_results = await self._run_task_variation(
                task_variation, config, i + 1
            )

            results["variations"][f"variation_{i+1}"] = variation_results

            # Update summary
            if variation_results["success"]:
                results["summary"]["successful"] += 1
            else:
                results["summary"]["failed"] += 1

            results["summary"]["total_runs"] += variation_results["total_runs"]

        self._logger.info(
            f"Completed all variations. Success: {results['summary']['successful']}, Failed: {results['summary']['failed']}"
        )
        return results

    async def _run_task_variation(
        self,
        task_variation: TaskConfig,
        config: ExperimentConfiguration,
        variation_index: int,
    ) -> Dict[str, Any]:
        """Run a single task variation over all target datasets."""
        variation_results = {
            "name": task_variation.name,
            "description": task_variation.description,
            "variation_index": variation_index,
            "success": True,
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "dataset_results": {},
            "errors": [],
            "step_configs": {
                step.name: step.config for step in task_variation.steps if step.config
            },
        }

        # Get all target datasets from step and task evaluations
        all_datasets = set()

        # Add step-level datasets
        for step in task_variation.steps:
            step_datasets = config.get_target_datasets_for_step(step.name)
            self._logger.info(f"Step '{step.name}' target datasets: {step_datasets}")
            all_datasets.update(step_datasets)

        # Add task-level datasets
        task_datasets = config.get_target_datasets_for_task()
        self._logger.info(f"Task-level target datasets: {task_datasets}")
        all_datasets.update(task_datasets)

        self._logger.info(
            f"All target datasets for variation {variation_index}: {all_datasets}"
        )

        if not all_datasets:
            self._logger.warning("No target datasets found in evaluation configuration")
            return variation_results

        # Run evaluation on each dataset
        for dataset_name in all_datasets:
            self._logger.info(f"🔍 Starting evaluation for dataset: {dataset_name}")

            try:
                dataset_result = await self._evaluate_dataset_for_variation(
                    dataset_name, task_variation, config, variation_index
                )

                variation_results["dataset_results"][dataset_name] = dataset_result
                variation_results["total_runs"] += 1

                if dataset_result["success"]:
                    variation_results["successful_runs"] += 1
                    self._logger.info(
                        f"✅ Dataset evaluation successful: {dataset_name}"
                    )
                else:
                    variation_results["failed_runs"] += 1
                    variation_results["errors"].extend(dataset_result.get("errors", []))
                    self._logger.error(f"❌ Dataset evaluation failed: {dataset_name}")

            except Exception as e:
                error_msg = f"Failed to evaluate dataset {dataset_name}: {e}"
                self._logger.error(error_msg)
                variation_results["dataset_results"][dataset_name] = {
                    "success": False,
                    "error": error_msg,
                }
                variation_results["total_runs"] += 1
                variation_results["failed_runs"] += 1
                variation_results["errors"].append(error_msg)

        # Determine overall success
        if variation_results["failed_runs"] > 0:
            variation_results["success"] = False

        return variation_results

    async def _evaluate_dataset_for_variation(
        self,
        dataset_name: str,
        task_variation: TaskConfig,
        config: ExperimentConfiguration,
        variation_index: int,
    ) -> Dict[str, Any]:
        """Evaluate a dataset for a specific task variation."""
        try:
            self._logger.info(
                f"🔍 Evaluating dataset '{dataset_name}' for variation {variation_index}"
            )

            # Determine which step this dataset corresponds to
            step_name = self._extract_step_name_from_dataset(
                dataset_name, task_variation
            )
            self._logger.info(
                f"📋 Extracted step name from dataset '{dataset_name}': {step_name}"
            )

            # Get evaluation configuration for this step
            evaluators = []
            if step_name:
                # Step-level evaluation
                self._logger.info(
                    f"🔧 Getting step-level evaluations for step: {step_name}"
                )
                step_evaluations = config.get_evaluation_config(step_name)
                self._logger.info(f"📊 Step evaluations found: {len(step_evaluations)}")
                for eval_config in step_evaluations:
                    self._logger.info(
                        f"🔧 Creating evaluator: {eval_config.get('name', 'unnamed')} (type: {eval_config.get('type', 'unknown')})"
                    )
                    # Convert dict to EvaluatorConfig if needed
                    if isinstance(eval_config, dict):
                        from .config_models import EvaluatorConfig

                        eval_config = EvaluatorConfig(**eval_config)
                    evaluator_func = evaluator_factory.create_evaluator(eval_config)
                    evaluators.append(evaluator_func)

            # Also add task-level evaluations if available
            self._logger.info("🔧 Getting task-level evaluations")
            task_evaluations = (
                config.get_evaluation_config()
            )  # No step_name = task level
            self._logger.info(f"📊 Task evaluations found: {len(task_evaluations)}")
            for eval_config in task_evaluations:
                self._logger.info(
                    f"🔧 Creating evaluator: {eval_config.get('name', 'unnamed')} (type: {eval_config.get('type', 'unknown')})"
                )
                # Convert dict to EvaluatorConfig if needed
                if isinstance(eval_config, dict):
                    from .config_models import EvaluatorConfig

                    eval_config = EvaluatorConfig(**eval_config)
                evaluator_func = evaluator_factory.create_evaluator(eval_config)
                evaluators.append(evaluator_func)

            self._logger.info(f"📊 Total evaluators created: {len(evaluators)}")

            if not evaluators:
                self._logger.warning(f"No evaluators found for dataset: {dataset_name}")
                return {
                    "success": True,
                    "evaluator_count": 0,
                    "reason": "No evaluators configured",
                }

            # Create experiment prefix
            experiment_prefix = f"{config.settings.get('experiment_prefix', 'experiment')}_variation_{variation_index}_{dataset_name}"
            self._logger.info(f"🏷️  Experiment prefix: {experiment_prefix}")

            # Run evaluation using LangSmith's aevaluate
            self._logger.info(
                f"🚀 Running evaluation with {len(evaluators)} evaluators on {dataset_name} for variation {variation_index}"
            )

            # Prepare metadata safely
            base_metadata = {
                "experiment_name": config.name,
                "variation_index": variation_index,
                "variation_name": task_variation.name,
                "dataset_name": dataset_name,
                "evaluation_type": "task_variation_evaluation",
                "evaluator_count": len(evaluators),
                "step_name": step_name,
                "variation_config": {
                    step.name: step.config
                    for step in task_variation.steps
                    if step.config
                },
            }

            # Add settings metadata if available
            if hasattr(config, "settings") and config.settings:
                if isinstance(config.settings, dict) and "metadata" in config.settings:
                    base_metadata.update(config.settings["metadata"])

            results = await aevaluate(
                RunnableLambda(lambda x: x),  # Identity function for dataset evaluation
                dataset_name,  # Dataset name
                evaluators=evaluators,
                experiment_prefix=experiment_prefix,
                description=f"Variation {variation_index}: {task_variation.description or 'No description'} on {dataset_name}",
                metadata=base_metadata,
            )

            # Extract results information
            result_info = {
                "success": True,
                "results_type": type(results).__name__,
                "evaluator_count": len(evaluators),
                "experiment_prefix": experiment_prefix,
                "step_name": step_name,
                "langsmith_results": results,
            }

            # Try to get more detailed results
            if hasattr(results, "results") and results.results:
                result_info["evaluation_count"] = len(results.results)
                result_info["has_detailed_results"] = True
            else:
                result_info["evaluation_count"] = 0
                result_info["has_detailed_results"] = False

            self._logger.info(
                f"Successfully evaluated dataset: {dataset_name} for variation {variation_index}"
            )
            return result_info

        except Exception as e:
            error_msg = f"Evaluation failed for dataset {dataset_name} in variation {variation_index}: {e}"
            self._logger.error(error_msg)
            return {"success": False, "error": error_msg, "dataset_name": dataset_name}

    def _extract_step_name_from_dataset(
        self, dataset_name: str, task_variation: TaskConfig
    ) -> Optional[str]:
        """Extract step name from dataset name to determine which step to evaluate."""
        # This is a simple heuristic - in practice, you might want more sophisticated matching
        for step in task_variation.steps:
            if step.name in dataset_name:
                return step.name
        return None

    def run_sync(self, coro):
        """Run an async coroutine in a sync context."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)


# Convenience function for running experiments
async def run_yaml_experiments(config: ExperimentConfiguration) -> Dict[str, Any]:
    """Convenience function to run experiments from configuration."""
    runner = YAMLExperimentRunner()
    return await runner.run_experiments_from_config(config)


def run_yaml_experiments_sync(config: ExperimentConfiguration) -> Dict[str, Any]:
    """Synchronous version of run_yaml_experiments."""
    runner = YAMLExperimentRunner()
    return runner.run_sync(run_yaml_experiments(config))
