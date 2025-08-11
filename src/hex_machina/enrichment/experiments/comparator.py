"""
Experiment comparator for analyzing and comparing experiment results.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.hex_machina.enrichment.experiments.runner import ExperimentRunner

logger = logging.getLogger(__name__)


class ExperimentComparator:
    """Compares and analyzes experiment results."""

    def __init__(self):
        self.runner = ExperimentRunner()

    def compare_experiment_results(self, experiment_name: str) -> Dict[str, Any]:
        """
        Compare results from multiple runs of the same experiment.

        Args:
            experiment_name: Name of the experiment to compare

        Returns:
            Comparison results
        """
        # Get all results for this experiment
        results = self.runner.list_experiment_results(experiment_name)

        if not results:
            return {"error": f"No results found for experiment: {experiment_name}"}

        comparison = {
            "experiment_name": experiment_name,
            "total_runs": len(results),
            "runs": [],
            "summary": {},
            "trends": {},
        }

        # Analyze each run
        for result in results:
            run_analysis = self._analyze_single_run(result)
            comparison["runs"].append(run_analysis)

        # Generate summary
        comparison["summary"] = self._generate_comparison_summary(comparison["runs"])

        # Analyze trends
        comparison["trends"] = self._analyze_trends(comparison["runs"])

        return comparison

    def _analyze_single_run(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single experiment run."""
        analysis = {
            "file": result.get("file"),
            "started_at": result.get("started_at"),
            "completed_at": result.get("completed_at"),
            "duration": self._calculate_duration(
                result.get("started_at"), result.get("completed_at")
            ),
            "configurations": {},
            "best_configuration": result.get("summary", {}).get("best_configuration"),
            "best_score": result.get("summary", {}).get("best_score"),
            "success_rate": result.get("summary", {}).get("successful_runs", 0)
            / max(result.get("summary", {}).get("total_configurations", 1), 1),
        }

        # Analyze each configuration
        for config_name, eval_result in result.get("evaluation_results", {}).items():
            config_analysis = self._analyze_configuration(config_name, eval_result)
            analysis["configurations"][config_name] = config_analysis

        return analysis

    def _analyze_configuration(
        self, config_name: str, eval_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze results for a single configuration."""
        if "error" in eval_result:
            return {"error": eval_result["error"]}

        analysis = {
            "config_name": config_name,
            "scores": {},
            "average_score": 0,
            "has_error": False,
        }

        # Extract scores
        total_score = 0
        score_count = 0

        for evaluator_name, score in eval_result.items():
            if isinstance(score, dict) and "score" in score:
                score_value = score["score"]
            elif isinstance(score, (int, float)):
                score_value = score
            else:
                continue

            analysis["scores"][evaluator_name] = score_value
            total_score += score_value
            score_count += 1

        if score_count > 0:
            analysis["average_score"] = total_score / score_count

        return analysis

    def _generate_comparison_summary(
        self, runs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate summary across all runs."""
        if not runs:
            return {}

        summary = {
            "total_runs": len(runs),
            "average_duration": 0,
            "best_overall_score": -1,
            "best_overall_config": None,
            "most_consistent_config": None,
            "config_performance": {},
        }

        # Calculate average duration
        total_duration = sum(run.get("duration", 0) for run in runs)
        summary["average_duration"] = total_duration / len(runs)

        # Find best overall score
        for run in runs:
            if run.get("best_score", -1) > summary["best_overall_score"]:
                summary["best_overall_score"] = run.get("best_score", -1)
                summary["best_overall_config"] = run.get("best_configuration")

        # Analyze configuration performance across runs
        config_scores = {}
        for run in runs:
            for config_name, config_analysis in run.get("configurations", {}).items():
                if "error" in config_analysis:
                    continue

                if config_name not in config_scores:
                    config_scores[config_name] = []

                config_scores[config_name].append(
                    config_analysis.get("average_score", 0)
                )

        # Calculate statistics for each configuration
        for config_name, scores in config_scores.items():
            if scores:
                summary["config_performance"][config_name] = {
                    "average_score": sum(scores) / len(scores),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "std_dev": self._calculate_std_dev(scores),
                    "runs_count": len(scores),
                }

        # Find most consistent configuration (lowest std dev)
        most_consistent = None
        lowest_std_dev = float("inf")

        for config_name, perf in summary["config_performance"].items():
            if perf["std_dev"] < lowest_std_dev:
                lowest_std_dev = perf["std_dev"]
                most_consistent = config_name

        summary["most_consistent_config"] = most_consistent

        return summary

    def _analyze_trends(self, runs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends across runs."""
        if len(runs) < 2:
            return {"message": "Need at least 2 runs to analyze trends"}

        # Sort runs by completion time
        sorted_runs = sorted(runs, key=lambda x: x.get("completed_at", ""))

        trends = {"score_trend": [], "duration_trend": [], "success_rate_trend": []}

        for run in sorted_runs:
            trends["score_trend"].append(
                {
                    "timestamp": run.get("completed_at"),
                    "best_score": run.get("best_score", 0),
                }
            )

            trends["duration_trend"].append(
                {
                    "timestamp": run.get("completed_at"),
                    "duration": run.get("duration", 0),
                }
            )

            trends["success_rate_trend"].append(
                {
                    "timestamp": run.get("completed_at"),
                    "success_rate": run.get("success_rate", 0),
                }
            )

        return trends

    def _calculate_duration(
        self, started_at: Optional[str], completed_at: Optional[str]
    ) -> float:
        """Calculate duration in seconds."""
        if not started_at or not completed_at:
            return 0

        try:
            start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            return (end_time - start_time).total_seconds()
        except Exception:
            return 0

    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance**0.5

    def generate_comparison_report(
        self, experiment_name: str, output_dir: Optional[str] = None
    ) -> str:
        """Generate a detailed comparison report."""
        comparison = self.compare_experiment_results(experiment_name)

        if "error" in comparison:
            return comparison["error"]

        # Create output directory
        if output_dir is None:
            output_dir = Path("reports") / "experiments" / "comparisons"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_dir / f"{experiment_name}_comparison_{timestamp}.json"

        with open(report_file, "w") as f:
            json.dump(comparison, f, indent=2, default=str)

        logger.info(f"Generated comparison report: {report_file}")
        return str(report_file)
