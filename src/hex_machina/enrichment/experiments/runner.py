"""
Experiment runner for testing multiple task configurations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.hex_machina.enrichment.evaluation.evaluation_functions import (
    evaluate_dataset_examples,
)
from src.hex_machina.enrichment.evaluation.langsmith.datasets.dataset_manager import (
    EvaluationDatasetManager,
)
from src.hex_machina.enrichment.evaluation.langsmith_integration import (
    create_evaluation_experiment,
)
from src.hex_machina.enrichment.experiments.config import ExperimentConfig, TaskConfig
from src.hex_machina.enrichment.tasks.runner import task_runner
from src.hex_machina.storage.manager import get_storage_manager

logger = logging.getLogger(__name__)


class ExperimentRunner:
    """Runs experiments with multiple task configurations."""

    def __init__(self):
        self.storage_manager = get_storage_manager()
        self.dataset_manager = EvaluationDatasetManager()

    async def run_experiment(self, config: ExperimentConfig) -> Dict[str, Any]:
        """
        Run a complete experiment with multiple task configurations.

        Args:
            config: Experiment configuration

        Returns:
            Dictionary containing experiment results
        """
        logger.info(f"Starting experiment: {config.experiment_name}")

        # Create LangSmith experiment
        experiment_id = create_evaluation_experiment(config.experiment_name)

        results = {
            "experiment_name": config.experiment_name,
            "started_at": datetime.now().isoformat(),
            "config": config.dict(),
            "task_results": {},
            "evaluation_results": {},
            "summary": {},
        }

        # Run each task configuration
        for task_config in config.task_configs:
            try:
                logger.info(f"Running task configuration: {task_config.name}")

                # Run task with this configuration
                task_result = await self._run_task_config(
                    config, task_config, experiment_id
                )

                # Evaluate results
                evaluation_result = await self._evaluate_task_results(
                    config, task_config, task_result, experiment_id
                )

                results["task_results"][task_config.name] = task_result
                results["evaluation_results"][task_config.name] = evaluation_result

            except Exception as e:
                logger.error(f"Error running task config {task_config.name}: {e}")
                results["task_results"][task_config.name] = {"error": str(e)}
                results["evaluation_results"][task_config.name] = {"error": str(e)}

        # Generate summary
        results["summary"] = self._generate_summary(config, results)
        results["completed_at"] = datetime.now().isoformat()

        # Save results
        self._save_experiment_results(config.experiment_name, results)

        logger.info(f"Completed experiment: {config.experiment_name}")
        return results

    async def _run_task_config(
        self,
        experiment_config: ExperimentConfig,
        task_config: TaskConfig,
        experiment_id: str,
    ) -> Dict[str, Any]:
        """Run a single task configuration."""

        # Create dynamic task configuration
        dynamic_config = self._create_dynamic_task_config(task_config)

        # Run task on dataset
        workflow_operation_id = f"exp_{experiment_config.experiment_name}_{task_config.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task_results = await task_runner.run_task_on_source(
            task_name="ContentCompletenessLangChainTask",
            source_type="dataset",
            source_value=experiment_config.evaluation_dataset,
            task_config=dynamic_config,
            workflow_operation_id=workflow_operation_id,
        )

        return {
            "workflow_operation_id": workflow_operation_id,
            "articles_processed": len(task_results),
            "success_count": len(
                [r for r in task_results if not hasattr(r, "error") or not r.error]
            ),
            "error_count": len(
                [r for r in task_results if hasattr(r, "error") and r.error]
            ),
            "config_used": task_config.config,
            "results": task_results,
        }

    async def _evaluate_task_results(
        self,
        experiment_config: ExperimentConfig,
        task_config: TaskConfig,
        task_result: Dict[str, Any],
        experiment_id: str,
    ) -> Dict[str, Any]:
        """Evaluate results from a task configuration."""

        if "error" in task_result:
            return {"error": task_result["error"]}

        workflow_operation_id = task_result.get("workflow_operation_id")
        if not workflow_operation_id:
            return {"error": "No workflow operation ID found"}

        # Evaluate the results
        evaluation_result = evaluate_dataset_examples(
            dataset_name=experiment_config.evaluation_dataset,
            evaluators=experiment_config.evaluators,
            split=experiment_config.evaluation_split,
            experiment_name=f"{experiment_config.experiment_name}_{task_config.name}",
        )

        return evaluation_result

    def _create_dynamic_task_config(self, task_config: TaskConfig) -> Dict[str, Any]:
        """Create dynamic task configuration from experiment config."""
        # This would integrate with the existing task configuration system
        # For now, return the config as-is
        return task_config.config

    def _generate_summary(
        self, config: ExperimentConfig, results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate summary of experiment results."""
        summary = {
            "total_configurations": len(config.task_configs),
            "successful_runs": 0,
            "failed_runs": 0,
            "best_configuration": None,
            "scores": {},
        }

        # Count successful and failed runs
        for task_name, task_result in results["task_results"].items():
            if "error" in task_result:
                summary["failed_runs"] += 1
            else:
                summary["successful_runs"] += 1

        # Find best configuration based on primary metric
        best_score = -1
        best_config = None

        for task_name, eval_result in results["evaluation_results"].items():
            if "error" in eval_result:
                continue

            # Get primary metric score
            primary_metric = config.comparison_metrics.primary
            if primary_metric in eval_result:
                score = eval_result[primary_metric]
                if isinstance(score, dict) and "score" in score:
                    score_value = score["score"]
                elif isinstance(score, (int, float)):
                    score_value = score
                else:
                    continue

                summary["scores"][task_name] = score_value

                if score_value > best_score:
                    best_score = score_value
                    best_config = task_name

        summary["best_configuration"] = best_config
        summary["best_score"] = best_score

        return summary

    def _save_experiment_results(self, experiment_name: str, results: Dict[str, Any]):
        """Save experiment results to file."""
        # Create reports directory if it doesn't exist
        reports_dir = Path("reports") / "experiments"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = reports_dir / f"{experiment_name}_{timestamp}.json"

        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Saved experiment results to: {results_file}")

    def list_experiment_results(
        self, experiment_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List available experiment results."""
        reports_dir = Path("reports") / "experiments"
        if not reports_dir.exists():
            return []

        results = []
        for results_file in reports_dir.glob("*.json"):
            if experiment_name and experiment_name not in results_file.name:
                continue

            try:
                with open(results_file, "r") as f:
                    result_data = json.load(f)
                    result_data["file"] = str(results_file)
                    results.append(result_data)
            except Exception as e:
                logger.error(f"Error loading result file {results_file}: {e}")

        return sorted(results, key=lambda x: x.get("completed_at", ""), reverse=True)
